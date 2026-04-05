"""Crawl4ai scraping, URL rewriting, content extraction via trafilatura."""
import asyncio
import logging
import os
import random
import re
import sys

import trafilatura

from lib.logging import warn, progress
from lib.quality import score as quality_score
from lib.youtube import is_youtube_url, get_transcript

logging.getLogger("crawl4ai").setLevel(logging.ERROR)
logging.getLogger("playwright").setLevel(logging.ERROR)


def rewrite_url(url: str) -> str:
    return re.sub(r'https?://(www\.)?reddit\.com/', 'https://old.reddit.com/', url)


def extract_content(html: str) -> str | None:
    if not html:
        return None
    return trafilatura.extract(html, include_comments=True, include_tables=True)


async def scrape_urls(urls: list[str]) -> tuple[list, dict]:
    """Scrape a list of URLs with rate limiting. Returns (pages, log)."""
    from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

    browser_cfg = BrowserConfig(headless=True, enable_stealth=True, verbose=False)
    run_cfg = CrawlerRunConfig(simulate_user=True, magic=True, page_timeout=10000, verbose=False)
    log = {"blocked": 0}

    pages = []

    # Suppress playwright's stderr spam during browser init
    _stderr = sys.stderr
    sys.stderr = open(os.devnull, "w")
    try:
        ctx = AsyncWebCrawler(config=browser_cfg)
        crawler = await ctx.__aenter__()
    finally:
        sys.stderr.close()
        sys.stderr = _stderr

    try:
        i = 0
        with progress("Scraping", total=len(urls)) as advance:
            while i < len(urls):
                batch_size = random.randint(2, 4)
                batch = urls[i:i + batch_size]
                tasks = [crawler.arun(url=url, config=run_cfg) for url in batch]
                results_batch = await asyncio.gather(*tasks, return_exceptions=True)

                blocked_count = sum(
                    1 for rb in results_batch
                    if not isinstance(rb, Exception) and not rb.success and "403" in str(rb.error_message)
                )
                log["blocked"] += blocked_count
                pages.extend(results_batch)
                advance(len(batch))
                i += batch_size

                if blocked_count == len(results_batch):
                    break
                elif blocked_count > 0:
                    await asyncio.sleep(random.uniform(3, 6))
                elif i < len(urls):
                    await asyncio.sleep(random.uniform(1, 3))
    finally:
        await ctx.__aexit__(None, None, None)

    return pages, log


def process_pages(results: list[dict], pages: list) -> tuple[list[dict], dict]:
    """Extract content from scraped pages. Returns (entries, log)."""
    log = {"scraped": 0, "errors": 0}
    entries = []

    with progress("Analyzing", total=len(results)) as advance:
      for r, page in zip(results, pages):
        entry = {
            "title": r["title"],
            "url": r["url"],
            "snippet": r.get("content", ""),
            "content": None,
            "error": None,
        }
        if "_query" in r:
            entry["query"] = r["_query"]

        if is_youtube_url(r["url"]):
            transcript = get_transcript(r["url"])
            if transcript:
                entry["content"] = transcript
                entry["quality"] = quality_score(transcript, None, entry["url"], r.get("_query"))
                log["scraped"] += 1
            else:
                entry["error"] = "No transcript available"
                log["errors"] += 1
        elif isinstance(page, Exception):
            entry["error"] = str(page)
            log["errors"] += 1
        else:
            html = getattr(page, "html", None)
            if html:
                entry["html"] = html
                entry["content"] = extract_content(html)
                entry["quality"] = quality_score(entry["content"], html, entry["url"], r.get("_query"))
            if entry["content"] and len(entry["content"]) > 50:
                log["scraped"] += 1
            elif not page.success:
                entry["error"] = page.error_message
                log["errors"] += 1
        entries.append(entry)
        advance()

    return entries, log
