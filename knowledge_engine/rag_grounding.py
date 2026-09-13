"""
Retrieval-Augmented Grounding (RAG) module for AI Cortex Server.
Searches SQLite FTS5 knowledge base for official documentation from
Microsoft, Red Hat, Linux, AWS, GitHub, VMware, and Ubuntu.
"""

from typing import Optional, List, Dict
from knowledge_indexer import search_knowledge

def get_grounded_context(query: str, limit: int = 2) -> str:
    """Retrieves concise, high-relevance documentation context for fast CPU inference."""
    results = search_knowledge(query, limit=limit)
    if not results:
        return ""

    context_lines = [
        "### OFFICIAL VENDOR DOCUMENTATION REFERENCE:",
    ]
    for r in results:
        domain = r.get("domain", "").upper()
        title = r.get("title", "")
        section = r.get("section", "")
        text = r.get("text", "")
        code = r.get("code", "")
        
        context_lines.append(f"[{domain}] {title} ({section}):")
        context_lines.append(text[:400])
        if code:
            context_lines.append(f"Command/Config:\n```\n{code[:250]}\n```")
            
    context_lines.append("### END REFERENCE\n")
    return "\n".join(context_lines)

if __name__ == "__main__":
    test_q = "how to configure vswitch promiscuous mode in esxi"
    ctx = get_grounded_context(test_q)
    print("Test Grounding Context:\n", ctx)
