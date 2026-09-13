# AI Cortex Autonomous Learning Pipeline: Architecture Deep Dive

## 1. Overview
The AI Cortex Autonomous Learning Pipeline is an unattended, self-sustaining knowledge harvesting, indexing, dataset generation, and model retraining system designed for private, high-security infrastructure.

It bridges authoritative vendor documentation from **Microsoft**, **Red Hat**, **Linux (Kernel/TLDP)**, **Amazon Web Services (AWS)**, **GitHub**, **VMware (Broadcom)**, and **Ubuntu Server**, as well as the personal profile of **Chaminuka Mbanje**, into both a real-time Retrieval-Augmented Grounding (RAG) index and fine-tuned local LLM weights.

---

## 2. Subsystem Components

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                               AI Cortex Core Engine                             │
│                                                                                 │
│   [ doc_sources.py ] ──> [ harvester.py ] ──> [ knowledge_indexer.py ]         │
│            ▲                    │                        │                      │
│            │                    ▼                        ▼                      │
│   (Target Registry)    (Raw Markdown Storage)  (SQLite FTS5 + BM25)             │
│                                 │                        │                      │
│                                 ▼                        ▼                      │
│                      [ dataset_synthesizer.py ]   [ rag_grounding.py ]          │
│                                 │                        │                      │
│                                 ▼                        ▼                      │
│                     (training_dataset.jsonl)   (FastAPI /v1/chat/completions)   │
│                                 │                                               │
│                                 ▼                                               │
│                      [ modelfile_updater.py ]                                   │
│                                 │                                               │
│                                 ▼                                               │
│                        (Ollama Engine)                                          │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Stage 1: Document Harvester (`harvester.py` & `doc_sources.py`)
* **Registry Seeds**: `doc_sources.py` defines curated seed URLs and targeted search expressions for each domain.
* **HTML Cleaning**: `trafilatura` extracts clean semantic markdown text, discarding ads, headers, footers, and scripts while preserving tables, code blocks, and headings.
* **Domain Allowlist**: A strict URL verification filter ensures only authoritative vendor domains are fetched:
  * `*.microsoft.com`
  * `*.redhat.com`
  * `*.kernel.org`, `*.archlinux.org`, `*.tldp.org`, `*.man7.org`
  * `*.amazon.com`, `*.amazonaws.com`
  * `*.github.com`
  * `*.vmware.com`, `*.broadcom.com`
  * `*.ubuntu.com`
  * `*.schedmd.com`
* **Polite Scraping**: 1.5-second pacing per document to prevent rate-limiting.

### Stage 2: SQLite FTS5 Knowledge Indexer (`knowledge_indexer.py`)
* **Storage Engine**: SQLite in Write-Ahead Logging (WAL) mode (`PRAGMA journal_mode=WAL;`).
* **Chunking Algorithm**: Markdown documents are broken into logical sections by `#`, `##`, and `###` headers. Code blocks are extracted and indexed separately.
* **FTS5 Virtual Table**: Provides BM25 ranking across `domain`, `title`, `section`, and `chunk_text`.
* **Performance**: Sub-2ms query response time across 4,000+ indexed chunks.

### Stage 3: Instruction-Tuning Dataset Synthesizer (`dataset_synthesizer.py`)
* **Format**: ChatML JSON Lines (`{"messages": [{"role": "system", ...}, {"role": "user", ...}, {"role": "assistant", ...}]}`).
* **Pair Types**:
  1. *Section / Concept Q&A*: Synthesizes specific questions regarding architectural concepts and administrative procedures.
  2. *Command / Syntax Q&A*: Extracts code blocks and shell commands, creating practical task-based questions.
  3. *Best Practices Q&A*: Identifies keywords (`recommend`, `troubleshoot`, `security`, `failover`) and structures verified answers.
* **Deduplication**: MD5 hash set prevents repeated generation of identical questions across cycles.

### Stage 4: Modelfile Sync & Headless Compilation (`modelfile_updater.py`)
* **Dynamic System Prompt**: Aggregates the latest database metrics (`documents`, `chunks`, `domains`) and generates a structured system prompt embedding homelab rules and domain cheat sheets.
* **Headless Rebuilding**: Executes `ollama create ai-cortex -f /opt/ai-cortex/Modelfile` and `ollama create qwen2.5:7b -f /opt/ai-cortex/Modelfile` without interactive prompts.

### Stage 5: Retrieval-Augmented Grounding (`rag_grounding.py` & `agy_server.py`)
* **Live Ingestion**: Intercepts requests arriving at `http://192.168.0.235:8000/v1/chat/completions`.
* **Context Formatting**: Compact markdown references are injected into the system prompt prior to inference, ensuring zero hallucinations.
* **Dual Fallback**: Dispatches to Google Antigravity (Gemini) when verification is enabled, falling back to local Ollama on network timeouts or offline mode.

---

## 3. Unattended Daemon Execution (`auto_trainer.py`)

The pipeline runs continuously via systemd:
* **Service**: `ai-docs-trainer.service`
* **Execution Interval**: 1,800 seconds (30 minutes) between learning cycles.
* **Error Handling**: Graceful exception catching per stage with automatic recovery on next interval.
* **Logging**: Dual output to `stdout` and `/opt/ai-cortex/data/training_learner.log`.
