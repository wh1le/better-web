from lib.scrape import rewrite_url


def test_rewrites_reddit():
    assert rewrite_url("https://www.reddit.com/r/linux") == "https://www.old.reddit.com/r/linux"


def test_rewrites_reddit_without_www():
    assert rewrite_url("https://reddit.com/r/linux") == "https://old.reddit.com/r/linux"


def test_leaves_other_urls():
    assert rewrite_url("https://example.com/page") == "https://example.com/page"
