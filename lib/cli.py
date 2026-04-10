import asyncio
import os
import re
from datetime import datetime

import typer

from lib.dedup import deduplicate
from lib.digest import digest, find_latest, stats
from lib.logging import done, error, info, warn
from lib.output import output_path, save, slugify
from lib.scrape import process_pages, rewrite_url, scrape_urls
from lib.search import dedup, search

app = typer.Typer(help="Search, scrape, and digest the web.")



@app.command("search")
def search_cmd(
    queries: list[str],
    limit: int = 10,
    engines: str | None = None,
    quick: bool = typer.Option(False, "--quick", help="Print snippets only, no scraping"),
    copy: bool = typer.Option(True, "--no-copy", help="Skip copying digest to clipboard"),
    analyze_with_llm: bool = typer.Option(False, "--analyze-with-llm", help="Extract relevant info with local LLM"),
):
    """Search 1+ queries, scrape and save. --quick for snippets only."""
    all_results = []
    for q in queries:
        results = dedup(search(q, limit, engines))
        info(f"[dim]{len(results)}[/dim] {q}")
        for r in results:
            r["_query"] = q
        all_results.extend(results)

    seen = set()
    unique = []
    for r in all_results:
        url = re.sub(r'[?#].*', '', r["url"])
        if url not in seen:
            seen.add(url)
            unique.append(r)

    dupes = len(all_results) - len(unique)
    if len(queries) > 1:
        info(f"{len(unique)} unique" + (f" ({dupes} dupes removed)" if dupes else ""))

    if quick:
        for i, r in enumerate(unique, 1):
            print(f"### {i}. {r['title']}")
            print(f"URL: {r['url']}")
            print(f"{r.get('content', '')}")
            print()
        return

    async def _run():
        urls = [rewrite_url(r["url"]) for r in unique]
        pages, scrape_log = await scrape_urls(urls)
        entries, proc_log = process_pages(unique, pages)

        # content-level dedup (removes near-duplicate pages)
        before_dedup = len(entries)
        entries = deduplicate(entries)
        dedup_removed = before_dedup - len(entries)

        query_str = queries[0] if len(queries) == 1 else " ".join(queries)
        data = {
            "queries": queries,
            "mode": "search",
            "timestamp": datetime.now().isoformat(),
            "log": {**scrape_log, **proc_log, "total": len(unique), "dedup_removed": dedup_removed},
            "results": entries,
        }

        out_file = output_path("search", slugify(query_str))
        save(data, out_file)
        _summary(scrape_log, proc_log, entries)

        if copy:
            import subprocess
            text = digest(out_file)
            txt_file = out_file.replace(".json", ".txt")
            with open(txt_file, "w") as f:
                f.write(text)
            subprocess.run(["wl-copy"], input=text.encode(), check=True)
            s = stats(out_file)
            filtered = s.get('filtered', 0)
            msg = f"Copied to clipboard (~{s['tokens']:,} tokens, {s['usable']} pages)"
            if filtered:
                msg += f" [dim]({filtered} low-quality filtered out)[/dim]"
            info(msg)

    asyncio.run(_run())


@app.command()
def scrape(url: str):
    """Scrape a single URL and print clean text."""
    async def _run():
        pages, _ = await scrape_urls([rewrite_url(url)])
        page = pages[0] if pages else None
        if page is None or isinstance(page, Exception):
            error(f"Error: {page}")
            raise typer.Exit(1)
        from lib.scrape import extract_content
        html = getattr(page, "html", None)
        text = extract_content(html) if html else None
        if text:
            print(text)
        else:
            error("No content extracted")
            raise typer.Exit(1)

    asyncio.run(_run())


@app.command()
def digest_cmd(
    file: str | None = typer.Argument(None),
    raw: bool = False,
):
    """Extract clean text from research file for LLM."""
    path = file if file and os.path.isfile(file) else find_latest()
    if not path:
        error("No research files in output/")
        raise typer.Exit(1)

    if raw:
        print(digest(path))
        return

    s = stats(path)
    info(f"File:   {s['file']}")
    info(f"Query:  {s['query']}")
    filtered = s.get('filtered', 0)
    pages_str = f"{s['usable']}/{s['total']}"
    if filtered:
        pages_str += f" ({filtered} filtered as low quality)"
    info(f"Pages:  {pages_str}")
    info(f"Tokens: ~{s['tokens']:,}")

    if typer.confirm("\nSend to stdout?", default=False):
        print(digest(path))
    else:
        info("Aborted.")


@app.command()
def update_blocklist():
    """Download and update domain blocklists from configured sources."""
    from lib.filter import update_blocklists
    update_blocklists()

def _summary(scrape_log: dict, proc_log: dict, entries: list[dict]):
    chars = sum(len(e.get("content") or "") for e in entries if e.get("content") and len(e["content"]) > 50)
    tokens = chars // 4
    parts = [f"{proc_log['scraped']} scraped"]
    if scrape_log["blocked"]:
        parts.append(f"{scrape_log['blocked']} blocked")
    if proc_log["errors"]:
        parts.append(f"{proc_log['errors']} errors")
    parts.append(f"~{tokens:,} tokens")
    msg = ", ".join(parts)
    if scrape_log["blocked"] or proc_log["errors"]:
        warn(msg)
    else:
        done(msg)


if __name__ == "__main__":
    app()
