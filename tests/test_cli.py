import json
import os
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from lib.cli import app
from tests.conftest import (
    SEARX_SCRUB,
    search_vcr,
    load_html_fixtures,
    save_html_fixtures,
)

runner = CliRunner()
RECORD = os.environ.get("VCR_RECORD")
OUTPUT_DIR = Path(__file__).parent.parent / "output"
FIXTURE_NAME = "search_batch_pages"

QUERIES = [
    "how does the human gut microbiome affect mental health",
    "gut brain axis serotonin production explained",
]
LIMIT = "3"


def _latest_output():
    jsons = sorted(OUTPUT_DIR.glob("search-*.json"), key=os.path.getmtime)
    return jsons[-1] if jsons else None


def _run_search():
    if RECORD:
        result = runner.invoke(app, ["search", "--no-copy", "--limit", LIMIT] + list(QUERIES))
        out = _latest_output()
        if out:
            with out.open() as f:
                data = json.load(f)
            save_html_fixtures(FIXTURE_NAME, data["results"])
        return result

    url_map = load_html_fixtures(FIXTURE_NAME)

    from lib.settings import settings
    original_url = settings.searx_engine.url
    settings._config.set("searx_engine.url", SEARX_SCRUB)
    try:
        with patch("lib.scrape.rewrite_url", lambda url: url_map.get(url, url)):
            result = runner.invoke(app, ["search", "--no-copy", "--limit", LIMIT] + list(QUERIES))
    finally:
        settings._config.set("searx_engine.url", original_url)
    return result


def _load_output():
    out = _latest_output()
    if not out:
        return None
    with out.open() as f:
        return json.load(f)


# --- search pipeline ---

@search_vcr.use_cassette("cli_search_batch.yaml")
def test_search_exits_cleanly():
    result = _run_search()
    assert result.exit_code == 0


@search_vcr.use_cassette("cli_search_batch.yaml")
def test_search_creates_output_file():
    _run_search()
    assert _latest_output() is not None


@search_vcr.use_cassette("cli_search_batch.yaml")
def test_output_has_correct_structure():
    _run_search()
    data = _load_output()
    assert data is not None
    assert "queries" in data
    assert "mode" in data
    assert "timestamp" in data
    assert "log" in data
    assert "results" in data


@search_vcr.use_cassette("cli_search_batch.yaml")
def test_output_queries_match_input():
    _run_search()
    data = _load_output()
    assert data["queries"] == list(QUERIES)
    assert data["mode"] == "search"


@search_vcr.use_cassette("cli_search_batch.yaml")
def test_output_log_has_stats():
    _run_search()
    data = _load_output()
    log = data["log"]
    assert "scraped" in log
    assert "errors" in log
    assert "total" in log
    assert "blocked" in log
    assert "dedup_removed" in log
    assert log["total"] > 0


@search_vcr.use_cassette("cli_search_batch.yaml")
def test_output_results_have_content():
    _run_search()
    data = _load_output()
    results = data["results"]
    assert len(results) > 0
    for r in results:
        assert "title" in r
        assert "url" in r
        assert "content" in r


@search_vcr.use_cassette("cli_search_batch.yaml")
def test_output_results_have_quality_scores():
    _run_search()
    data = _load_output()
    scored = [r for r in data["results"] if r.get("quality")]
    assert len(scored) > 0
    for r in scored:
        q = r["quality"]
        assert "score" in q
        assert "flags" in q
        assert "page_type" in q
        assert "relevance" in q
        assert 0 <= q["score"] <= 100
        assert 0.0 <= q["relevance"] <= 1.0


@search_vcr.use_cassette("cli_search_batch.yaml")
def test_dedup_removed_duplicates():
    _run_search()
    data = _load_output()
    urls = [r["url"] for r in data["results"]]
    assert len(urls) == len(set(urls))


# --- digest ---

def test_digest_raw_outputs_text():
    out = _latest_output()
    if not out:
        return
    result = runner.invoke(app, ["digest", "--raw", str(out)])
    assert result.exit_code == 0
    assert "# Research:" in result.output


def test_digest_raw_contains_sources():
    out = _latest_output()
    if not out:
        return
    result = runner.invoke(app, ["digest", "--raw", str(out)])
    assert "##" in result.output
    assert "quality:" in result.output


def test_digest_info_shows_stats():
    out = _latest_output()
    if not out:
        return
    result = runner.invoke(app, ["digest", str(out)], input="n\n")
    assert result.exit_code == 0
    assert "File:" in result.output
    assert "Query:" in result.output
    assert "Pages:" in result.output
    assert "Tokens:" in result.output


# --- preview ---

def test_preview_shows_page():
    out = _latest_output()
    if not out:
        return
    result = runner.invoke(app, ["preview", str(out), "-i", "0"])
    assert result.exit_code == 0
    assert "quality:" in result.output
    assert "relevance:" in result.output
    assert "---" in result.output


def test_preview_shows_content():
    out = _latest_output()
    if not out:
        return
    result = runner.invoke(app, ["preview", str(out), "-i", "0"])
    assert len(result.output) > 200


def test_preview_bad_index_exits():
    out = _latest_output()
    if not out:
        return
    result = runner.invoke(app, ["preview", str(out), "-i", "999"])
    assert result.exit_code != 0


# --- quick mode ---

@search_vcr.use_cassette("cli_search_batch.yaml")
def test_search_quick_prints_snippets():
    result = runner.invoke(app, ["search", "--quick", "--limit", LIMIT] + list(QUERIES))
    assert result.exit_code == 0
    assert "###" in result.output
    assert "http" in result.output


# --- error handling ---

