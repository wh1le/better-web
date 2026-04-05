# Better Web

> **Personal MVP** — not packaged for general use. Partially vibe-coded, might have bugs. Built for my own research workflow.

Search the web, scrape pages, score content quality, filter out junk — copy clean results for LLM consumption. All results are saved as parsed, cleaned markdown — ready to read, pipe to an LLM, or re-export later.

Runs on simple hardware (tested on a ThinkPad with integrated graphics). No GPU required — the only ML model used is a small sentence-transformer (~80MB) for relevance scoring.

## Why

Search engines increasingly return SEO spam and low-quality content. LLM-powered search tools often hallucinate or give shallow answers. A simple research question shouldn't mean 25+ open tabs just to find a few good sources.

better-web automates the entire research workflow: query a private search engine, scrape results, score quality using multiple signals (domain reputation, AI detection, readability, semantic relevance), filter out the noise, and return focused, streamlined information ready for LLM summarization — all in one command.

## Demo

![demo](https://raw.githubusercontent.com/wh1le/better-web/main/assets/demo.gif)

## Dependencies

| Library | Purpose |
|---------|---------|
| [crawl4ai](https://github.com/unclecode/crawl4ai) | Headless browser scraping with stealth mode |
| [playwright](https://playwright.dev/python/) | Browser automation engine |
| [trafilatura](https://github.com/adbar/trafilatura) | Content extraction from HTML |
| [typer](https://typer.tiangolo.com/) | CLI framework |
| [rich](https://github.com/Textualize/rich) | Terminal formatting and progress bars |
| [textstat](https://github.com/textstat/textstat) | Readability metrics (Flesch Reading Ease, grade level) |
| [thinkst-zippy](https://github.com/thinkst/zippy) | AI detection (compression-based, no ML models) |
| [tranco](https://tranco-list.eu/) | Domain reputation scoring (top-1M ranking) |
| [tldextract](https://github.com/john-googler/tldextract) | Domain analysis and heuristics |
| [datasketch](https://github.com/ekzhu/datasketch) | MinHash LSH for near-duplicate detection |
| [sentence-transformers](https://www.sbert.net/) | Semantic relevance scoring (all-MiniLM-L6-v2) |
| [readability-lxml](https://github.com/buriy/python-readability) | Alternative readability extraction |
| [markdownify](https://github.com/matthewwithanm/python-markdownify) | HTML to markdown conversion |
| [youtube-transcript-api](https://github.com/jdepoix/youtube-transcript-api) | YouTube caption extraction |
| [yt-dlp](https://github.com/yt-dlp/yt-dlp) | YouTube video download (for whisper fallback) |
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | Audio transcription when no captions available |

Requires Python 3.12+.

## Setup

```bash
nix develop && poetry install
```

Requires a local [SearXNG](https://docs.searxng.org/) instance. The URL is hardcoded in `config.toml` under `[searx]` (default `http://localhost:8882/search`) — change it there to point to your instance.

## Usage

```bash
bw search "query"                     # search + scrape + score + copy
bw search "q1" "q2" --limit 20       # multi-query batch
bw search --quick "query"             # snippets only, no scraping
bw scrape "https://example.com"       # single URL to stdout
bw digest-cmd --raw                   # re-export latest research
bw update-blocklist                   # refresh domain blocklists
bin/agent                             # fzf picker -> copy/claude
```

## Pipeline

```
query -> SearXNG -> dedup -> blocklist filter -> scrape -> extract -> score -> dedup content -> filter -> rank -> clipboard
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

## Output

```markdown
# Research: python asyncio best practices
_Scored and ranked. 5 sources, 3 filtered out._

## [HIGH] AsyncIO Deep Dive - Real Python
quality: 72/100 | relevance: 0.81 | type: article
<content>
```

## Config

`config.toml` — SearXNG URL, scrape timing, quality threshold, blocklist sources. See file for details.
