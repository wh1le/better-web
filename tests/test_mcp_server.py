import asyncio
from unittest.mock import patch
from urllib.error import URLError

import pytest

from lib.mcp_server import BetterWebMCP
from tests.conftest import (
    SEARX_SCRUB,
    search_vcr,
    load_html_fixtures,
)

FIXTURE_NAME = "search_batch_pages"
QUERIES = ["how does the human gut microbiome affect mental health"]
LIMIT = 3


@pytest.fixture
def server():
    return BetterWebMCP()


@pytest.mark.asyncio
async def test_exposes_tools(server):
    tools = await server.mcp.list_tools()
    names = [tool.name for tool in tools]
    assert "health_check" in names
    assert "web_search" in names


@pytest.mark.asyncio
async def test_web_search_schema(server):
    tools = await server.mcp.list_tools()
    tool_map = {tool.name: tool for tool in tools}
    schema = tool_map["web_search"].inputSchema
    props = schema["properties"]
    assert "queries" in props
    assert "limit" in props
    assert schema["required"] == ["queries"]


@pytest.mark.asyncio
async def test_health_check_healthy(server):
    mock_resp = type("Resp", (), {"status": 200, "__enter__": lambda s: s, "__exit__": lambda *a: None})()
    with patch("lib.health.urllib.request.urlopen", return_value=mock_resp):
        result = await server.mcp.call_tool("health_check", {})
    text = result[0][0].text
    assert "healthy" in text


@pytest.mark.asyncio
async def test_health_check_unreachable(server):
    with patch("lib.health.urllib.request.urlopen", side_effect=URLError("connection refused")):
        result = await server.mcp.call_tool("health_check", {})
    text = result[0][0].text
    assert "unreachable" in text.lower()


@pytest.mark.asyncio
@search_vcr.use_cassette("cli_search_batch.yaml")
async def test_web_search_returns_digest(server):
    url_map = load_html_fixtures(FIXTURE_NAME)

    from lib.settings import settings
    original_url = settings.searx_engine.url
    settings._config.set("searx_engine.url", SEARX_SCRUB)
    try:
        with patch("lib.scrape.rewrite_url", lambda url: url_map.get(url, url)):
            result = await server.mcp.call_tool("web_search", {"queries": QUERIES, "limit": LIMIT})
    finally:
        settings._config.set("searx_engine.url", original_url)

    content, _ = result
    text = content[0].text
    assert "# Research:" in text
    assert "##" in text
