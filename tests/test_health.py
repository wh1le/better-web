from unittest.mock import patch
from urllib.error import URLError

from lib.health import check_searx


def test_check_searx_healthy():
    mock_resp = type("Resp", (), {"status": 200, "__enter__": lambda s: s, "__exit__": lambda *a: None})()
    with patch("lib.health.urllib.request.urlopen", return_value=mock_resp):
        result = check_searx()
    assert result["status"] == "ok"
    assert result["http_status"] == 200
    assert "url" in result


def test_check_searx_unreachable():
    with patch("lib.health.urllib.request.urlopen", side_effect=URLError("connection refused")):
        result = check_searx()
    assert result["status"] == "error"
    assert "error" in result
    assert "url" in result


def test_check_searx_timeout():
    with patch("lib.health.urllib.request.urlopen", side_effect=TimeoutError("timed out")):
        result = check_searx()
    assert result["status"] == "error"
    assert "timed out" in result["error"]
