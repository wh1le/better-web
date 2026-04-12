import re
import sys
from datetime import datetime

from mcp.server.fastmcp import FastMCP

from lib.dedup import deduplicate
from lib.digest import digest
from lib.health import check_searx
from lib.output import output_path, save, slugify
from lib.scrape import process_pages, rewrite_url, scrape_urls
from lib.search import dedup, search


class BetterWebMCP:
    def __init__(self):
        self.mcp = FastMCP(
            "better-web",
            instructions="Web research tools: search, scrape, and digest web content.",
        )
        self._register_tools()

    def run(self, transport="stdio", host="127.0.0.1", port=8000):
        if transport == "stdio":
            self.mcp.run()
        else:
            self.mcp.run(transport=transport, host=host, port=port)

    def _register_tools(self):
        server = self

        @self.mcp.tool()
        def health_check() -> str:
            """Check if SearXNG search backend is reachable."""
            result = check_searx()
            if result["status"] == "ok":
                return f"SearXNG is healthy at {result['url']}"
            return f"SearXNG unreachable at {result['url']}: {result['error']}"

        @self.mcp.tool()
        async def web_search(queries: list[str], limit: int = 10) -> str:
            all_results = server._fetch(queries, limit)
            unique = server._dedup_urls(all_results)
            entries, scrape_log, proc_log, dedup_removed = await server._scrape(unique)
            out_file = server._save(queries, entries, scrape_log, proc_log, len(unique), dedup_removed)
            return digest(out_file)

    def _fetch(self, queries, limit):
        all_results = []
        for query in queries:
            results = dedup(search(query, limit))
            for result in results:
                result["_query"] = query
            all_results.extend(results)
        return all_results

    def _dedup_urls(self, results):
        seen = set()
        unique = []
        for result in results:
            url = re.sub(r"[?#].*", "", result["url"])
            if url not in seen:
                seen.add(url)
                unique.append(result)
        return unique

    async def _scrape(self, results):
        urls = [rewrite_url(result["url"]) for result in results]
        pages, scrape_log = await scrape_urls(urls)
        entries, proc_log = process_pages(results, pages)
        before = len(entries)
        entries = deduplicate(entries)
        return entries, scrape_log, proc_log, before - len(entries)

    def _save(self, queries, entries, scrape_log, proc_log, total, dedup_removed):
        query_str = queries[0] if len(queries) == 1 else " ".join(queries)
        data = {
            "queries": list(queries),
            "mode": "search",
            "timestamp": datetime.now().isoformat(),
            "log": {**scrape_log, **proc_log, "total": total, "dedup_removed": dedup_removed},
            "results": entries,
        }
        out_file = output_path("search", slugify(query_str))
        save(data, out_file)
        return out_file


def main():
    transport = "stdio"
    host = "127.0.0.1"
    port = 8000

    args = sys.argv[1:]
    for idx, arg in enumerate(args):
        if arg in ("--transport", "-t") and idx + 1 < len(args):
            transport = args[idx + 1]
        elif arg == "--host" and idx + 1 < len(args):
            host = args[idx + 1]
        elif arg in ("--port", "-p") and idx + 1 < len(args):
            port = int(args[idx + 1])

    BetterWebMCP().run(transport=transport, host=host, port=port)


if __name__ == "__main__":
    main()
