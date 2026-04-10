import pytest

from lib.settings import CONFIG_PATH, DATA_DIR, ROOT, Settings

SAMPLE_CONFIG = """\
searx_engine:
  url: "http://test:8888/search"
  max_pages: 5
  delay: 0.5
blocklists:
  - name: test-list
    url: "http://example.com/list.txt"
"""

SAMPLE_LIST = """\
one
two
# skip
three
"""

PADDED_LIST = """\
  foo
  bar
"""


@pytest.fixture
def cfg(tmp_path):
    (tmp_path / "config.yaml").write_text(SAMPLE_CONFIG)
    return Settings(str(tmp_path / "config.yaml"))


@pytest.fixture
def data(tmp_path):
    d = tmp_path / "data"
    d.mkdir()
    (d / "things.txt").write_text(SAMPLE_LIST)
    (d / "padded.txt").write_text(PADDED_LIST)
    (tmp_path / "config.yaml").write_text("scoring:\n  baseline: 50\n")
    return Settings(str(tmp_path / "config.yaml"), data_dir=d)


def test_reads_config(cfg):
    assert cfg.searx_engine.url == "http://test:8888/search"
    assert cfg.searx_engine.max_pages == 5


def test_reads_blocklists(cfg):
    assert cfg.blocklists[0]["name"] == "test-list"


def test_loads_txt(data):
    assert data._load_list("things") == ["one", "two", "three"]


def test_strips_whitespace(data):
    assert data._load_list("padded") == ["foo", "bar"]


def test_real_lists():
    s = Settings()
    assert ".pdf" in s.skip_extensions
    assert "edu" in s.high_quality_tlds
    assert "xyz" in s.low_quality_tlds
    assert "best" in s.seo_keywords
    assert len(s.ai_phrases) > 0
    assert "replied" in s.discussion_markers
    assert "linkedin.com" in s.custom_blocked


def test_sets_are_sets():
    s = Settings()
    for prop in (s.skip_extensions, s.high_quality_tlds, s.low_quality_tlds, s.seo_keywords):
        assert isinstance(prop, set)


def test_constants():
    assert CONFIG_PATH.name == "config.yaml"
    assert DATA_DIR.name == "data"
    assert (ROOT / "pyproject.toml").exists()
