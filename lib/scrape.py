"""Crawl4ai scraping, URL rewriting, content extraction via trafilatura."""
import asyncio
import logging
import os
import random
import sys

import trafilatura

from lib.logging import info, progress, step
from lib.quality import score as quality_score
from lib.settings import settings
from lib.youtube import get_transcript, is_youtube_url

logging.getLogger("crawl4ai").setLevel(logging.ERROR)
logging.getLogger("playwright").setLevel(logging.ERROR)


def rewrite_url(url: str) -> str:
    for src, dst in settings.url_rewrites.items():
        url = url.replace(src, dst)
    return url


def extract_content(html: str) -> str | None:
    if not html:
        return None
    return trafilatura.extract(html, include_comments=True, include_tables=True)


async def scrape_urls(urls: list[str]) -> tuple[list, dict]:
    """Scrape a list of URLs with rate limiting. Returns (pages, log)."""
    step("Scrape")
    from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

    scrape_settings = settings.scrape
    batch_min, batch_max = scrape_settings.batch
    delay_min, delay_max = scrape_settings.delay
    backoff_min, backoff_max = scrape_settings.backoff

    browser_cfg = BrowserConfig(headless=True, enable_stealth=True, verbose=False)
    run_cfg = CrawlerRunConfig(
        simulate_user=True, magic=True,
        page_timeout=scrape_settings.timeout, verbose=False,
    )
    log = {"blocked": 0}

    pages = []

    # Suppress playwright's stderr spam during browser init
    _stderr = sys.stderr
    sys.stderr = open(os.devnull, "w")  # noqa: SIM115
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
                batch_size = random.randint(batch_min, batch_max)
                batch = urls[i:i + batch_size]
                tasks = [crawler.arun(url=url, config=run_cfg) for url in batch]
                results_batch = await asyncio.gather(*tasks, return_exceptions=True)

                blocked_count = sum(
                    bool(not isinstance(rb, BaseException) and not rb.success and "403" in str(rb.error_message))
                    for rb in results_batch
                )
                log["blocked"] += blocked_count
                pages.extend(results_batch)
                advance(len(batch))
                i += batch_size

                if blocked_count == len(results_batch):
                    break
                elif blocked_count > 0:
                    await asyncio.sleep(random.uniform(backoff_min, backoff_max))
                elif i < len(urls):
                    await asyncio.sleep(random.uniform(delay_min, delay_max))
    finally:
        await ctx.__aexit__(None, None, None)

    fetched = sum(1 for p in pages if not isinstance(p, Exception) and getattr(p, "success", False))
    msg = f"fetched {fetched}/{len(urls)} pages"
    if log["blocked"]:
        msg += f", {log['blocked']} blocked"
    info(f"[dim]{msg}[/dim]")
    return pages, log


def process_pages(results: list[dict], pages: list) -> tuple[list[dict], dict]:
    """Extract content from scraped pages. Returns (entries, log)."""
    step("Score")
    log = {"scraped": 0, "errors": 0}
    entries = []

    with progress("Scoring", total=len(results)) as advance:
        for result, page in zip(results, pages, strict=False):
            entry = {
                "title": result["title"],
                "url": result["url"],
                "snippet": result.get("content", ""),
                "content": None,
                "error": None,
            }
            if "_query" in result:
                entry["query"] = result["_query"]

            if is_youtube_url(result["url"]):
                transcript = get_transcript(result["url"])
                if transcript:
                    entry["content"] = transcript
                    entry["quality"] = quality_score(transcript, None, entry["url"], result.get("_query"))
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
                    entry["quality"] = quality_score(entry["content"], html, entry["url"], result.get("_query"))
                if entry["content"] and len(entry["content"]) > settings.scoring.min_text:
                    log["scraped"] += 1
                elif not page.success:
                    entry["error"] = page.error_message
                    log["errors"] += 1
            entries.append(entry)
            advance()

    scored = [e for e in entries if e.get("quality")]
    high = sum(1 for e in scored if e["quality"].get("score", 0) >= 70)
    med = sum(1 for e in scored if 45 <= e["quality"].get("score", 0) < 70)
    low = sum(1 for e in scored if e["quality"].get("score", 0) < 45)
    info(f"[dim]{high} high, {med} med, {low} low[/dim]")

    return entries, log
