from unittest.mock import patch

from lib.domain_filter import DomainFilter, _parse_ublacklist_line, _load_blocklist_file


UBLACKLIST_CONTENT = """\
*://*.spam.com/*
*://junk.xyz/*
# comment
!title line
plainbad.net
"""


@patch("lib.domain_filter.settings")
def test_blocks_custom_domain(mock_settings):
    mock_settings.custom_blocked = ["blocked.com"]
    f = DomainFilter()
    assert f.is_blocked("https://blocked.com/page")


@patch("lib.domain_filter.settings")
def test_blocks_subdomain(mock_settings):
    mock_settings.custom_blocked = ["blocked.com"]
    f = DomainFilter()
    assert f.is_blocked("https://sub.blocked.com/page")


@patch("lib.domain_filter.settings")
def test_allows_clean_domain(mock_settings):
    mock_settings.custom_blocked = ["blocked.com"]
    f = DomainFilter()
    assert not f.is_blocked("https://example.com/page")


@patch("lib.domain_filter.settings")
def test_strips_www(mock_settings):
    mock_settings.custom_blocked = ["blocked.com"]
    f = DomainFilter()
    assert f.is_blocked("https://www.blocked.com/page")


@patch("lib.domain_filter.settings")
def test_handles_bad_url(mock_settings):
    mock_settings.custom_blocked = []
    f = DomainFilter()
    assert not f.is_blocked("not-a-url")


def test_parse_ublacklist_wildcard():
    assert _parse_ublacklist_line("*://*.spam.com/*") == "spam.com"


def test_parse_ublacklist_plain():
    assert _parse_ublacklist_line("plainbad.net") == "plainbad.net"


def test_parse_ublacklist_comment():
    assert _parse_ublacklist_line("# comment") is None


def test_parse_ublacklist_empty():
    assert _parse_ublacklist_line("") is None


def test_load_blocklist_file(tmp_path):
    f = tmp_path / "list.txt"
    f.write_text(UBLACKLIST_CONTENT)
    domains = _load_blocklist_file(str(f))
    assert "spam.com" in domains
    assert "junk.xyz" in domains
    assert "plainbad.net" in domains
    assert len(domains) == 3


def test_load_blocklist_missing():
    domains = _load_blocklist_file("/nonexistent/path.txt")
    assert domains == set()
