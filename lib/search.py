"""SearXNG search, deduplication, filtering."""
import json
import os
import re
import time
import urllib.parse
import urllib.request

from lib.filter import is_blocked
from lib.logging import info
from lib.settings import settings


def _fetch_page(query: str, page: int, engines: str | None = None) -> list[dict]:
    p: dict[str, str | int] = {"q": query, "format": "json", "pageno": page}
    if engines:
        p["engines"] = engines
    params = urllib.parse.urlencode(p)
    req = urllib.request.Request(f"{settings.searx_engine.url}?{params}")
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
    results: list[dict] = data.get("results", [])
    return results


def search(query: str, limit: int = 100, engines: str | None = None) -> list[dict]:
    """Search SearXNG. Fetches one page at a time, filters, continues if needed."""
    skip_ext = settings.skip_extensions
    seen: set[str] = set()
    out: list[dict] = []
    skipped_ext = 0
    skipped_blocked = 0
    page = 1

    while len(out) < limit and page <= settings.searx_engine.max_pages:
        batch = _fetch_page(query, page, engines)
        if not batch:
            break

        filtered_this_page = 0
        for r in batch:
            url = re.sub(r'[?#].*', '', r["url"])
            ext = os.path.splitext(url.split("?")[0])[1].lower()
            if ext in skip_ext:
                skipped_ext += 1
                filtered_this_page += 1
                continue
            if is_blocked(url):
                skipped_blocked += 1
                filtered_this_page += 1
                continue
            if url not in seen:
                seen.add(url)
                out.append(r)

        # only fetch next page if we lost results to filtering and still need more
        if filtered_this_page > 0 and len(out) < limit:
            time.sleep(settings.searx_engine.delay)
            page += 1
        else:
            break

    if skipped_ext:
        info(f"Skipped {skipped_ext} non-HTML files")
    if skipped_blocked:
        info(f"Filtered {skipped_blocked} blocked domains")

    return out[:limit]


def dedup(results: list[dict]) -> list[dict]:
    """Cross-query dedup for batch mode. Per-query filtering already done in search()."""
    seen = set()
    out = []
    for r in results:
        url = re.sub(r'[?#].*', '', r["url"])
        if url not in seen:
            seen.add(url)
            out.append(r)
    return out
