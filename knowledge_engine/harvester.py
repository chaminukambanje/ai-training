"""
Documentation Harvester for AI Cortex Knowledge Engine.
Automates downloading, cleaning, and extracting documentation across:
Microsoft, Red Hat, Linux, AWS, GitHub, VMware, Ubuntu.
"""

import os
import re
import time
import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Set
from urllib.parse import urlparse

import httpx
import trafilatura
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS

from doc_sources import DOCUMENTATION_TARGETS
from knowledge_indexer import index_document, init_knowledge_db, get_stats

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("doc_harvester")

RAW_DOCS_DIR = Path("/opt/ai-cortex/knowledge/raw")

ALLOWED_DOMAINS = [
    "microsoft.com", "redhat.com", "kernel.org", "archlinux.org", 
    "tldp.org", "man7.org", "amazon.com", "amazonaws.com", 
    "github.com", "vmware.com", "broadcom.com", "ubuntu.com", 
    "schedmd.com", "linuxfoundation.org"
]

def is_authoritative_url(url: str) -> bool:
    try:
        from urllib.parse import urlparse
        netloc = urlparse(url).netloc.lower()
        return any(d in netloc for d in ALLOWED_DOMAINS)
    except Exception:
        return False


def url_to_slug(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path.strip("/").replace("/", "_").replace(".", "_")
    if not path:
        path = "index"
    url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
    clean_path = re.sub(r'[^a-zA-Z0-9_\-]', '', path)[:80]
    return f"{clean_path}_{url_hash}"

def fetch_and_clean_url(url: str) -> Dict:
    """Fetches URL and extracts clean structured markdown/text."""
    logger.info(f"Fetching documentation URL: {url}")
    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            # Fallback with custom headers via httpx
            headers = {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
            }
            resp = httpx.get(url, headers=headers, follow_redirects=True, timeout=25.0)
            if resp.status_code == 200:
                downloaded = resp.text

        if not downloaded:
            logger.warning(f"Could not download content for {url}")
            return {}

        # Extract structured text using trafilatura
        text = trafilatura.extract(
            downloaded,
            include_links=False,
            include_images=False,
            include_tables=True,
            output_format="markdown"
        )
        
        # Extract title
        soup = BeautifulSoup(downloaded, "lxml")
        title_tag = soup.find("title")
        h1_tag = soup.find("h1")
        title = ""
        if h1_tag and h1_tag.text.strip():
            title = h1_tag.text.strip()
        elif title_tag and title_tag.text.strip():
            title = title_tag.text.strip()
        else:
            title = urlparse(url).path.split("/")[-1]

        if not text or len(text.strip()) < 120:
            # Fallback text extraction using BS4
            for s in soup(["script", "style", "nav", "footer", "header", "aside"]):
                s.decompose()
            text = soup.get_text(separator="\n", strip=True)

        return {
            "url": url,
            "title": title,
            "content": text
        }
    except Exception as e:
        logger.error(f"Error harvesting {url}: {e}")
        return {}

def harvest_domain(domain_name: str, max_search_urls: int = 5) -> int:
    """Harvests seeds and dynamic search queries for a given domain."""
    config = DOCUMENTATION_TARGETS.get(domain_name)
    if not config:
        logger.error(f"Unknown domain: {domain_name}")
        return 0

    init_knowledge_db()
    domain_dir = RAW_DOCS_DIR / domain_name
    domain_dir.mkdir(parents=True, exist_ok=True)

    urls_to_fetch: Set[str] = {u for u in config.get("seed_urls", []) if is_authoritative_url(u)}

    # Discover deep docs using search queries
    for query in config.get("search_queries", []):
        try:
            time.sleep(1.0)
            logger.info(f"Searching official docs: {query}")
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_search_urls))
                for r in results:
                    href = r.get("href")
                    if href and href.startswith("http"):
                        # Keep within domain or authoritative sources
                        if is_authoritative_url(href): urls_to_fetch.add(href)
        except Exception as e:
            logger.warning(f"Search query error '{query}': {e}")

    logger.info(f"Targeting {len(urls_to_fetch)} URLs for {domain_name.upper()}")
    indexed_count = 0

    for url in urls_to_fetch:
        slug = url_to_slug(url)
        dest_file = domain_dir / f"{slug}.md"
        
        # If already downloaded recently, read from cache
        content = ""
        title = ""
        if dest_file.exists() and dest_file.stat().st_size > 200:
            logger.info(f"Loading cached doc: {dest_file.name}")
            with open(dest_file, "r", encoding="utf-8") as f:
                content = f.read()
            title = slug.replace("_", " ").title()
        else:
            time.sleep(1.5)  # Polite crawling rate limit
            doc = fetch_and_clean_url(url)
            if doc and doc.get("content"):
                title = doc.get("title", slug)
                content = doc.get("content", "")
                with open(dest_file, "w", encoding="utf-8") as f:
                    f.write(f"# {title}\n\nSource: {url}\n\n{content}")

        if content:
            chunks = index_document(domain_name, title, url, content)
            if chunks > 0:
                indexed_count += 1
                logger.info(f"Indexed {chunks} chunks for: {title[:60]}")

    return indexed_count

def harvest_all():
    """Runs through all 7 documentation domains."""
    total = 0
    for domain in DOCUMENTATION_TARGETS.keys():
        logger.info(f"=== Starting Harvester for: {domain.upper()} ===")
        count = harvest_domain(domain, max_search_urls=4)
        logger.info(f"Indexed {count} docs for {domain.upper()}")
        total += count
    logger.info(f"Finished harvesting! Total documents indexed: {total}")
    logger.info(f"Knowledge DB Stats: {get_stats()}")
    return total

if __name__ == "__main__":
    harvest_all()
