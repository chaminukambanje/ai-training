"""
Continuous Training Dataset Synthesizer for AI Cortex.
Converts ingested documentation chunks across Microsoft, Red Hat, Linux, AWS,
GitHub, VMware, and Ubuntu into ChatML instruction-tuning datasets.
Appends high-quality verified training pairs to /opt/ai-cortex/data/training_dataset.jsonl.
"""

import os
import re
import json
import sqlite3
import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Set

from knowledge_indexer import get_db_connection

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("dataset_synthesizer")

DATASET_FILE = Path("/opt/ai-cortex/data/training_dataset.jsonl")
PROCESSED_CHUNKS_FILE = Path("/opt/ai-cortex/data/processed_chunks.json")

SYSTEM_PROMPT = (
    "You are AI Cortex, the private intelligence assistant and systems copilot for "
    "Munashe Banjec's homelab infrastructure. Ground every response in verified "
    "system telemetry and official technical documentation."
)

def load_existing_prompts() -> Set[str]:
    seen = set()
    if DATASET_FILE.exists():
        with open(DATASET_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    for m in data.get("messages", []):
                        if m.get("role") == "user":
                            seen.add(hashlib.md5(m["content"].strip().lower().encode()).hexdigest())
                except Exception:
                    pass
    return seen

def synthesize_pairs_from_chunk(domain: str, title: str, section: str, text: str, code: str) -> List[Dict]:
    """Generates structured instruction pairs from a documentation chunk."""
    pairs = []
    
    # Clean text
    clean_text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text).strip()
    if len(clean_text) < 150:
        return []

    domain_tag = domain.capitalize()
    
    # 1. Section / Concept explanation Q&A
    if section and section.lower() not in ["overview", "part 1", "index", "introduction"]:
        user_q = f"In {domain_tag} ({title}), how do you configure or manage {section}?"
        answer = (
            f"According to official {domain_tag} documentation for '{title}', here is the guidance for {section}:\n\n"
            f"{clean_text}\n"
        )
        if code:
            answer += f"\nRelevant command syntax / configuration:\n```\n{code}\n```"
        pairs.append({"user": user_q, "assistant": answer.strip()})

    # 2. Extract specific command or code examples
    if code:
        lines = [l.strip() for l in code.splitlines() if l.strip() and not l.startswith("#")]
        if lines:
            primary_cmd = lines[0]
            user_q = f"What is the official {domain_tag} command or procedure to execute: `{primary_cmd[:60]}`?"
            answer = (
                f"In official {domain_tag} documentation ({title} - {section}):\n\n"
                f"Command / Configuration:\n```\n{code}\n```\n\n"
                f"Context and usage notes:\n{clean_text[:600]}..."
            )
            pairs.append({"user": user_q, "assistant": answer.strip()})

    # 3. Best practice / Sysadmin guideline Q&A
    if any(k in clean_text.lower() for k in ["recommend", "troubleshoot", "error", "security", "failover", "best practice", "warning"]):
        user_q = f"What are the official {domain_tag} best practices and troubleshooting recommendations for {title}?"
        answer = (
            f"Based on official {domain_tag} documentation ({title}):\n\n"
            f"{clean_text[:900]}\n"
        )
        if code:
            answer += f"\n\nExample implementation:\n```\n{code}\n```"
        pairs.append({"user": user_q, "assistant": answer.strip()})

    return pairs

def generate_training_data() -> int:
    """Reads unharvested chunks from DB and writes instruction dataset entries."""
    DATASET_FILE.parent.mkdir(parents=True, exist_ok=True)
    seen_prompts = load_existing_prompts()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, domain, title, section, chunk_text, code_snippets FROM chunks")
    rows = cursor.fetchall()
    conn.close()

    new_samples = 0
    with open(DATASET_FILE, "a", encoding="utf-8") as f:
        for r in rows:
            chunk_id, domain, title, section, text, code = r
            pairs = synthesize_pairs_from_chunk(domain, title, section, text, code)
            
            for p in pairs:
                q_hash = hashlib.md5(p["user"].strip().lower().encode()).hexdigest()
                if q_hash in seen_prompts:
                    continue
                seen_prompts.add(q_hash)
                
                entry = {
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": p["user"]},
                        {"role": "assistant", "content": p["assistant"]}
                    ]
                }
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                new_samples += 1

    logger.info(f"Synthesizer added {new_samples} new instruction-tuning samples to {DATASET_FILE}")
    return new_samples

if __name__ == "__main__":
    generate_training_data()
