"""
Knowledge Indexer & High-Speed Grounding Engine for AI Cortex.
Stores and indexes documentation using SQLite with FTS5 full-text search.
Provides BM25 ranking and instant context retrieval for the AI LLM server.
"""

import os
import re
import sqlite3
import datetime
from pathlib import Path
from typing import List, Dict, Optional

DB_PATH = Path("/opt/ai-cortex/knowledge/cortex_knowledge.db")

def get_db_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn

def init_knowledge_db():
    conn = get_db_connection()
    try:
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    domain TEXT NOT NULL,
                    title TEXT NOT NULL,
                    url TEXT UNIQUE,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    doc_id INTEGER NOT NULL,
                    domain TEXT NOT NULL,
                    title TEXT NOT NULL,
                    section TEXT,
                    chunk_text TEXT NOT NULL,
                    code_snippets TEXT,
                    FOREIGN KEY (doc_id) REFERENCES documents (id) ON DELETE CASCADE
                );
            """)
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                    domain,
                    title,
                    section,
                    chunk_text,
                    content='chunks',
                    content_rowid='id'
                );
            """)
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
                    INSERT INTO chunks_fts(rowid, domain, title, section, chunk_text)
                    VALUES (new.id, new.domain, new.title, new.section, new.chunk_text);
                END;
            """)
            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
                    INSERT INTO chunks_fts(chunks_fts, rowid, domain, title, section, chunk_text)
                    VALUES ('delete', old.id, old.domain, old.title, old.section, old.chunk_text);
                END;
            """)
    finally:
        conn.close()

def chunk_markdown(content: str, max_chars: int = 1500) -> List[Dict]:
    """Splits markdown into logical sections by headers and paragraphs."""
    sections = []
    lines = content.splitlines()
    current_title = "Overview"
    current_lines = []
    
    for line in lines:
        if line.startswith("#"):
            if current_lines:
                text = "\n".join(current_lines).strip()
                if len(text) > 40:
                    sections.append({"section": current_title, "text": text})
                current_lines = []
            current_title = line.lstrip("#").strip()
        else:
            current_lines.append(line)
            
    if current_lines:
        text = "\n".join(current_lines).strip()
        if len(text) > 40:
            sections.append({"section": current_title, "text": text})
            
    if not sections:
        paras = [p.strip() for p in content.split("\n\n") if len(p.strip()) > 50]
        for i, p in enumerate(paras):
            sections.append({"section": f"Part {i+1}", "text": p})

    chunks = []
    for sec in sections:
        text = sec["text"]
        code_blocks = re.findall(r"```(?:[a-zA-Z0-9_\-]+)?\n(.*?)```", text, re.DOTALL)
        code_str = "\n---\n".join(code_blocks) if code_blocks else ""
        
        if len(text) <= max_chars:
            chunks.append({
                "section": sec["section"],
                "text": text,
                "code": code_str
            })
        else:
            words = text.split()
            current_chunk = []
            curr_len = 0
            sub_idx = 1
            for word in words:
                current_chunk.append(word)
                curr_len += len(word) + 1
                if curr_len >= max_chars:
                    c_text = " ".join(current_chunk)
                    c_codes = re.findall(r"```(?:[a-zA-Z0-9_\-]+)?\n(.*?)```", c_text, re.DOTALL)
                    chunks.append({
                        "section": f"{sec['section']} (Part {sub_idx})",
                        "text": c_text,
                        "code": "\n---\n".join(c_codes) if c_codes else ""
                    })
                    current_chunk = []
                    curr_len = 0
                    sub_idx += 1
            if current_chunk:
                c_text = " ".join(current_chunk)
                chunks.append({
                    "section": f"{sec['section']} (Part {sub_idx})",
                    "text": c_text,
                    "code": ""
                })
    return chunks

def index_document(domain: str, title: str, url: str, content: str) -> int:
    """Inserts or updates a document and its chunk embeddings in FTS5."""
    if not content or len(content.strip()) < 100:
        return 0
        
    init_knowledge_db()
    conn = get_db_connection()
    chunks = chunk_markdown(content)
    
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM documents WHERE url = ?", (url,))
            row = cursor.fetchone()
            if row:
                doc_id = row[0]
                cursor.execute("UPDATE documents SET title = ?, content = ? WHERE id = ?", (title, content, doc_id))
                cursor.execute("DELETE FROM chunks WHERE doc_id = ?", (doc_id,))
            else:
                cursor.execute(
                    "INSERT INTO documents (domain, title, url, content) VALUES (?, ?, ?, ?)",
                    (domain, title, url, content)
                )
                doc_id = cursor.lastrowid

            for c in chunks:
                cursor.execute(
                    "INSERT INTO chunks (doc_id, domain, title, section, chunk_text, code_snippets) VALUES (?, ?, ?, ?, ?, ?)",
                    (doc_id, domain, title, c["section"], c["text"], c["code"])
                )
        return len(chunks)
    finally:
        conn.close()

def search_knowledge(query: str, domain: Optional[str] = None, limit: int = 3) -> List[Dict]:
    """Performs BM25-ranked full text search against official documentation."""
    init_knowledge_db()
    conn = get_db_connection()
    clean_query = re.sub(r'[^a-zA-Z0-9_\-\s]', ' ', query)
    tokens = [t.strip() for t in clean_query.split() if len(t.strip()) > 2]
    if not tokens:
        conn.close()
        return []

    fts_query = " OR ".join(f'"{t}"*' for t in tokens[:8])
    
    results = []
    try:
        cursor = conn.cursor()
        if domain:
            sql = """
                SELECT c.domain, c.title, c.section, c.chunk_text, c.code_snippets, d.url, rank
                FROM chunks_fts f
                JOIN chunks c ON f.rowid = c.id
                JOIN documents d ON c.doc_id = d.id
                WHERE chunks_fts MATCH ? AND c.domain = ?
                ORDER BY rank
                LIMIT ?
            """
            cursor.execute(sql, (fts_query, domain, limit))
        else:
            sql = """
                SELECT c.domain, c.title, c.section, c.chunk_text, c.code_snippets, d.url, rank
                FROM chunks_fts f
                JOIN chunks c ON f.rowid = c.id
                JOIN documents d ON c.doc_id = d.id
                WHERE chunks_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """
            cursor.execute(sql, (fts_query, limit))
            
        for row in cursor.fetchall():
            results.append({
                "domain": row[0],
                "title": row[1],
                "section": row[2],
                "text": row[3],
                "code": row[4],
                "url": row[5],
                "score": row[6]
            })
    except Exception as e:
        print(f"FTS search error: {e}")
    finally:
        conn.close()
    return results

def get_stats() -> Dict:
    init_knowledge_db()
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM documents")
        docs_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM chunks")
        chunks_count = cursor.fetchone()[0]
        cursor.execute("SELECT domain, COUNT(*) FROM documents GROUP BY domain")
        domain_counts = {row[0]: row[1] for row in cursor.fetchall()}
        return {
            "documents": docs_count,
            "chunks": chunks_count,
            "domains": domain_counts
        }
    finally:
        conn.close()

if __name__ == "__main__":
    init_knowledge_db()
    print("Database initialized:", get_stats())
