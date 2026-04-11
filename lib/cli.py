import asyncio
import json
import os
import re
import sys
from datetime import datetime

import click
from rich.console import Console

from lib.dedup import deduplicate
from lib.digest import digest, find_latest, stats
from lib.logging import done, error, info, warn
from lib.output import output_path, save, slugify
from lib.scrape import process_pages, rewrite_url, scrape_urls
from lib.search import dedup, search

out = Console()


@click.group()
def app():
    """Search, scrape, and digest the web."""


@app.command("search")
@click.argument("queries", nargs=-1, required=True)
@click.option("--limit", default=10, help="Max results per query")
@click.option("--engines", default=None, help="SearXNG engines to use")
@click.option("--quick", is_flag=True, help="Print snippets only, no scraping")
@click.option("--no-copy", is_flag=True, help="Skip copying digest to clipboard")
def search_cmd(queries, limit, engines, quick, no_copy):
    """Search 1+ queries, scrape and save."""
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
            out.print(f"[bold]### {i}. {r['title']}[/bold]")
            out.print(f"[dim]{r['url']}[/dim]")
            out.print(r.get("content", ""))
            out.print()
        return

    async def _run():
        urls = [rewrite_url(r["url"]) for r in unique]
        pages, scrape_log = await scrape_urls(urls)
        entries, proc_log = process_pages(unique, pages)

        before_dedup = len(entries)
        entries = deduplicate(entries)
        dedup_removed = before_dedup - len(entries)

        query_str = queries[0] if len(queries) == 1 else " ".join(queries)
        data = {
            "queries": list(queries),
            "mode": "search",
            "timestamp": datetime.now().isoformat(),
            "log": {**scrape_log, **proc_log, "total": len(unique), "dedup_removed": dedup_removed},
            "results": entries,
        }

        out_file = output_path("search", slugify(query_str))
        save(data, out_file)
        _summary(scrape_log, proc_log, entries)

        if not no_copy:
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
@click.argument("url")
def scrape(url):
    """Scrape a single URL and print clean text."""
    async def _run():
        pages, _ = await scrape_urls([rewrite_url(url)])
        page = pages[0] if pages else None
        if page is None or isinstance(page, Exception):
            error(f"Error: {page}")
            sys.exit(1)
        from lib.scrape import extract_content
        html = getattr(page, "html", None)
        text = extract_content(html) if html else None
        if text:
            out.print(text)
        else:
            error("No content extracted")
            sys.exit(1)

    asyncio.run(_run())


@app.command("digest")
@click.argument("file", required=False)
@click.option("--raw", is_flag=True, help="Print raw digest text")
def digest_cmd(file, raw):
    """Extract clean text from research file for LLM."""
    path = file if file and os.path.isfile(file) else find_latest()
    if not path:
        error("No research files in output/")
        sys.exit(1)

    if raw:
        out.print(digest(path))
        return

    s = stats(path)
    info(f"[bold]File:[/bold]   {s['file']}")
    info(f"[bold]Query:[/bold]  {s['query']}")
    filtered = s.get('filtered', 0)
    pages_str = f"{s['usable']}/{s['total']}"
    if filtered:
        pages_str += f" ({filtered} filtered as low quality)"
    info(f"[bold]Pages:[/bold]  {pages_str}")
    info(f"[bold]Tokens:[/bold] ~{s['tokens']:,}")

    if click.confirm("\nSend to stdout?", default=False):
        out.print(digest(path))
    else:
        info("Aborted.")


@app.command()
@click.argument("file", required=False)
@click.option("--index", "-i", default=0, help="Page index to preview")
def preview(file, index):
    """Render a scraped page as clean markdown."""
    from lib.render import html_to_markdown

    path = file if file and os.path.isfile(file) else find_latest()
    if not path:
        error("No research files in output/")
        sys.exit(1)

    with open(path) as f:
        data = json.load(f)

    results = data["results"]
    if index >= len(results):
        error(f"Index {index} out of range (0-{len(results) - 1})")
        sys.exit(1)

    r = results[index]
    q = r.get("quality", {})

    out.print(f"[bold]# {r.get('title', 'Untitled')}[/bold]")
    out.print()
    out.print(f"[dim]{r['url']}[/dim]")
    out.print()
    score = q.get("score", "?")
    rel = q.get("relevance", 0.0)
    ptype = q.get("page_type", "unknown")
    out.print(f"[cyan]quality:[/cyan] {score}/100 | [cyan]relevance:[/cyan] {rel} | [cyan]type:[/cyan] {ptype}")
    flags = q.get("flags", [])
    if flags:
        out.print(f"[cyan]flags:[/cyan] {', '.join(flags)}")
    out.print()
    out.print("[dim]---[/dim]")
    out.print()

    html = r.get("html")
    if html:
        out.print(html_to_markdown(html, r.get("url", "")))
    else:
        out.print(r.get("content") or "No content extracted.")


@app.command("update-blocklist")
def update_blocklist():
    """Download and update domain blocklists."""
    from lib.domain_filter import domain_filter
    domain_filter.update()


def _summary(scrape_log, proc_log, entries):
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
