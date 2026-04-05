# better-web

Search the web, scrape pages, score content quality, filter out junk — copy clean results for LLM consumption.

## Setup

```bash
nix develop && poetry install
```

Requires local [SearXNG](https://docs.searxng.org/) (default `localhost:8882`). Configure in `config.toml`.

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
