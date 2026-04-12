# Better Web

> Currently in alpha. Code quality and performance are not well optimized. MVP proved to be useful. I am working on refactoring, MCP, and a better CLI in the dev branch. Will get merged soon.

Terminal-first web research tool. Search the web, scrape pages, score content quality, filter out junk — get clean markdown ready for LLM consumption.

![demo](https://raw.githubusercontent.com/wh1le/better-web/main/assets/demo.gif)

## Why

Search engines increasingly return SEO spam and low-quality content. LLM-powered search tools often hallucinate or give shallow answers. A simple research question shouldn't mean 25+ open tabs just to find a few good sources.

better-web automates the entire research workflow: query a private search engine, scrape results, score quality using multiple signals (domain reputation, AI detection, readability, semantic relevance), filter out the noise, and return focused, clean markdown — all in one command.

No GPU required — runs on simple hardware. The only ML model used is a small sentence-transformer (~80MB) for relevance scoring.

## Prerequisites

- Python 3.12+
- A local [SearXNG](https://docs.searxng.org/) instance for search queries

**Quick SearXNG setup with Docker:**

```bash
docker run -d --name searxng -p 8882:8080 searxng/searxng
```

## Setup

**With Nix (recommended):**

```bash
nix develop && poetry install
```

**With pipx (isolated install):**

```bash
pipx install git+https://github.com/wh1le/better-web.git
playwright install chromium
```

**Without Nix:**

```bash
pip install poetry
poetry install
playwright install chromium
```

Configure your SearXNG URL in `config.yaml` under `searx_engine` (default `http://localhost:8882/search`).

## Usage

```bash
bw search "query"                     # search + scrape + score + copy
bw search "q1" "q2" --limit 20       # multi-query batch
bw search --quick "query"             # snippets only, no scraping
bw scrape "https://example.com"       # single URL to stdout
bw digest --raw                       # re-export latest research
bw preview                            # render page as clean markdown
bw update-blocklist                   # refresh domain blocklists
bin/explore                           # fzf picker -> preview in editor
bin/agent                             # fzf picker -> copy/claude
```

## Scoring

Every page gets 0-100 based on:

| Signal | Tool | What |
|--------|------|------|
| Domain reputation | [tranco](https://tranco-list.eu/) | Top-1M ranking, boost only (unranked = neutral) |
| Domain heuristics | [tldextract](https://github.com/john-googler/tldextract) | Junk TLDs, hyphen stuffing, SEO keywords, year in name |
| AI detection | [zippy](https://github.com/thinkst/zippy) | Compression-based, no ML models, no API keys |
| Readability | [textstat](https://github.com/textstat/textstat) | Flesch Reading Ease, grade level |
| Relevance | [sentence-transformers](https://www.sbert.net/) | Cosine similarity between query and content |
| HTML structure | built-in | Code blocks, comments, link density, nav ratio, ad scripts |
| Text heuristics | built-in | Keyword stuffing, repetitive bigrams, slop phrases, thin content |
| Content dedup | [datasketch](https://github.com/ekzhu/datasketch) | MinHash LSH, removes near-duplicate pages |

Pages below `min_quality_score` (default 30) are filtered out. Remaining pages are sorted best-first and tier-labeled (`HIGH`/`MED`/`LOW`).

## MCP Server

Expose better-web as an MCP server for Claude, Gemini, Cursor, and other AI agents.

<details>
<summary>Claude Code</summary>
<pre>
claude mcp add better-web -- pipx run better-web
</pre>
</details>

<details>
<summary>Claude Desktop</summary>
<p>Add to <code>claude_desktop_config.json</code>:</p>
<pre lang="json">
{
  "mcpServers": {
    "better-web": {
      "command": "nix",
      "args": ["develop", "/path/to/better-web", "--command", "bw-mcp"]
    }
  }
}
</pre>
</details>

<details>
<summary>Cursor</summary>
<p>Start the server first: <code>bw-mcp --transport http --port 8000</code></p>
<p>Add to <code>.cursor/mcp.json</code>:</p>
<pre lang="json">
{
  "mcpServers": {
    "better-web": {
      "type": "http",
      "url": "http://localhost:8000/mcp"
    }
  }
}
</pre>
</details>

<details>
<summary>Gemini CLI</summary>
<pre lang="json">
{
  "mcpServers": {
    "better-web": {
      "command": "nix",
      "args": ["develop", "/path/to/better-web", "--command", "bw-mcp"]
    }
  }
}
</pre>
</details>

## Config

`config.yaml` — SearXNG URL, scrape timing, quality thresholds, blocklist sources. Static lists (TLDs, blocked domains, AI phrases) live in `data/*.txt`.

## TODO

- [ ] Publish to PyPI
- [ ] Support XDG configuration path at `~/.config/bw`

## License

MIT
