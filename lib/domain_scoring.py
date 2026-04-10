"""Domain reputation scoring and page type classification."""
import re

import tldextract

from lib.settings import settings

try:
    from tranco import Tranco
    _tranco_list = Tranco(cache=True).list()
except Exception:
    _tranco_list = None


def domain_score(url: str) -> tuple[int, list[str], dict]:
    """Score domain from URL. Returns (points, flags, details)."""
    points = 0
    flags: list[str] = []
    details: dict[str, object] = {}

    ext = tldextract.extract(url)
    domain = ext.registered_domain
    name = ext.domain
    suffix = ext.suffix

    if not domain:
        return 0, ["bad_url"], {}

    details["domain"] = domain

    # tranco rank — boost only, never penalize unranked domains
    rank: int = _tranco_list.rank(domain) if _tranco_list else -1
    details["tranco_rank"] = rank
    if rank > 0:
        if rank <= 1000:
            points += 15
            flags.append("top_1k")
        elif rank <= 10000:
            points += 10
            flags.append("top_10k")
        elif rank <= 100000:
            points += 5
            flags.append("top_100k")
        else:
            points += 2

    # TLD signals
    if suffix in settings.lists.high_quality_tlds:
        points += 5
        flags.append("institutional_tld")
    elif suffix in settings.lists.low_quality_tlds:
        points -= 10
        flags.append("junk_tld")

    # domain name heuristics
    if name.count("-") >= 3:
        points -= 10
        flags.append("hyphen_stuffed")

    if len(name) > 30:
        points -= 5
        flags.append("long_domain")

    if re.search(r'20[2-3]\d', name):
        points -= 8
        flags.append("year_in_domain")

    name_words = set(name.lower().split("-"))
    seo_overlap = name_words & settings.lists.seo_keywords
    if seo_overlap:
        points -= 8
        flags.append(f"seo_domain:{','.join(seo_overlap)}")

    return points, flags, details


def page_type(url: str) -> str:
    """Classify page type from URL patterns."""
    path = url.lower().split("?")[0]
    if re.search(r'/questions/\d+|/answers?/', path):
        return "qa"
    if '/wiki/' in path or '.wiki.' in path:
        return "wiki"
    if re.search(r'/docs?/|/documentation/|\.readthedocs\.|/reference/', path):
        return "docs"
    if re.search(r'/blob/|/tree/|/commit/|/pull/|/issues?/', path):
        return "code"
    if re.search(r'/comments?/|/discuss|/forum|/thread', path):
        return "discussion"
    if re.search(r'/blog/|/posts?/|/article', path):
        return "article"
    if re.search(r'/product/|/buy/|/pricing|/shop/', path):
        return "product"
    return "unknown"
