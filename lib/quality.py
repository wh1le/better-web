"""Content quality scoring: textstat + zippy + domain reputation + HTML signals + heuristics."""
import re
import statistics
from collections import Counter

import textstat
import tldextract

from lib.settings import settings

try:
    from tranco import Tranco
    _tranco_list = Tranco(cache=True).list()
except Exception:
    _tranco_list = None

try:
    from zippy.zippy import EnsembledZippy
    _zippy = EnsembledZippy()

    def _ai_score(text: str) -> float:
        """Return 1.0 if AI-detected, 0.0 if human."""
        try:
            label, _conf = _zippy.run_on_text_chunked(text)
            return 1.0 if label == "AI" else 0.0
        except Exception:
            return 0.0
except ImportError:
    def _ai_score(_text: str) -> float:  # type: ignore[misc]
        return 0.0


# --- domain reputation ---

def _domain_score(url: str) -> tuple[int, list[str], dict]:
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


# --- page type from URL ---

def _page_type(url: str) -> str:
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


# --- HTML structural signals ---

def _html_signals(html: str, text: str) -> tuple[int, list[str], dict]:
    """Score based on HTML structure. Returns (points, flags, details)."""
    points = 0
    flags: list[str] = []
    details: dict[str, object] = {}

    html_lower = html.lower()
    text_len = max(len(text), 1)

    # code blocks
    code_blocks = len(re.findall(r'<code[\s>]', html_lower))
    pre_blocks = len(re.findall(r'<pre[\s>]', html_lower))
    total_code = code_blocks + pre_blocks
    if total_code >= 2:
        points += 10
        flags.append("has_code")
    elif total_code == 1:
        points += 5
        flags.append("has_code")
    details["code_blocks"] = total_code

    # article tag
    if '<article' in html_lower:
        points += 3
        flags.append("has_article_tag")

    # comment/reply sections
    comment_markers = re.findall(r'class="[^"]*comment[^"]*"', html_lower)
    if len(comment_markers) >= 3:
        points += 5
        flags.append("has_comments")
        details["comment_sections"] = len(comment_markers)

    # link density
    link_count = len(re.findall(r'<a[\s>]', html_lower))
    density: float = link_count / (text_len / 100)
    details["link_density"] = round(density, 2)
    if density > 3.0:
        points -= 10
        flags.append("high_link_density")
    elif density > 2.0:
        points -= 5

    # nav-to-content ratio
    nav_len = sum(len(m) for m in re.findall(r'<nav[\s>].*?</nav>', html_lower, re.DOTALL))
    if nav_len > 0:
        nav_ratio: float = nav_len / max(len(html), 1)
        details["nav_ratio"] = round(nav_ratio, 3)
        if nav_ratio > 0.3:
            points -= 5
            flags.append("nav_heavy")

    # ad/tracker scripts
    ad_patterns = re.findall(
        r'(adsbygoogle|googletag|doubleclick|adsense|taboola|outbrain|'
        r'analytics\.js|gtag|fbevents|hotjar)', html_lower
    )
    details["ad_scripts"] = len(ad_patterns)
    if len(ad_patterns) >= 4:
        points -= 5
        flags.append("ad_heavy")

    return points, flags, details


# --- text quality heuristics ---

def _text_signals(text: str) -> tuple[int, list[str], dict]:
    """Score based on text content. Returns (points, flags, details)."""
    scoring = settings.scoring
    points = 0
    flags: list[str] = []
    details: dict[str, object] = {}

    words = text.split()
    word_count = len(words)
    sentences = [sent.strip() for sent in re.split(r'[.!?]+', text) if len(sent.strip()) > 5]

    # readability
    flesch = textstat.flesch_reading_ease(text)
    details["flesch_reading_ease"] = round(flesch, 1)
    details["grade_level"] = round(textstat.flesch_kincaid_grade(text), 1)
    if flesch < 10:
        points -= 5
        flags.append("very_hard_to_read")
    elif 30 <= flesch <= 70:
        points += 5

    # AI detection
    ai = _ai_score(text)
    details["ai_score"] = round(ai, 2)
    if ai > 0.5:
        points += scoring.ai_penalty
        flags.append("likely_ai")

    # content length
    details["word_count"] = word_count
    if word_count < 100:
        points -= 25
        flags.append("thin")
    elif word_count < 200:
        points -= 10
        flags.append("short")
    elif word_count > 500:
        points += 5

    # keyword stuffing
    long_words = [w.lower() for w in words if len(w) > 4]
    if long_words:
        freq = Counter(long_words)
        top_word, top_count = freq.most_common(1)[0]
        ratio = top_count / len(long_words)
        if ratio > 0.05:
            points -= 10
            flags.append(f"keyword_stuffing:{top_word}")
            details["keyword_stuffing_ratio"] = round(ratio, 3)

    # repetitive bigrams
    if word_count > 20:
        bigrams = [f"{words[i]} {words[i+1]}" for i in range(len(words) - 1)]
        bigram_freq = Counter(bigrams)
        repeated = sum(1 for _, count in bigram_freq.items() if count > 3)
        repeat_ratio = repeated / max(len(bigrams), 1)
        if repeat_ratio > 0.05:
            points -= 10
            flags.append("repetitive")
            details["repetitive_bigram_ratio"] = round(repeat_ratio, 3)

    # sentence length variance
    if len(sentences) > 5:
        lengths = [len(sent.split()) for sent in sentences]
        mean = statistics.mean(lengths)
        if mean > 0:
            coefficient_of_variation = statistics.stdev(lengths) / mean
            details["sentence_variance"] = round(coefficient_of_variation, 2)
            if coefficient_of_variation < 0.3:
                points -= 5
                flags.append("uniform_sentences")

    # slop phrases
    text_lower = text.lower()
    slop_count = sum(1 for phrase in settings.lists.slop_phrases if phrase in text_lower)
    if slop_count >= 3:
        points -= 15
        flags.append(f"slop_phrases:{slop_count}")
    elif slop_count >= 1:
        points -= 3
    details["slop_phrase_count"] = slop_count

    # discussion signals
    discussion_count = sum(1 for marker in settings.lists.discussion_markers if marker in text_lower)
    if discussion_count >= 2:
        points += 10
        flags.append("discussion")

    return points, flags, details


# --- main scorer ---

def score(text: str, html: str | None = None, url: str | None = None, query: str | None = None) -> dict:
    """Score content quality. Returns dict with score (0-100), flags, details, page_type, relevance."""
    scoring = settings.scoring
    relevance_thresholds = scoring.relevance

    if not text or len(text.strip()) < scoring.min_text:
        return {"score": 0, "flags": ["empty"], "details": {}, "page_type": "unknown", "relevance": 0.0}

    total_points = scoring.baseline
    all_flags: list[str] = []
    all_details: dict[str, object] = {}

    # domain reputation
    if url:
        pts, flg, det = _domain_score(url)
        total_points += pts
        all_flags.extend(flg)
        all_details["domain"] = det

    # page type
    ptype = _page_type(url) if url else "unknown"

    # HTML structure
    if html:
        pts, flg, det = _html_signals(html, text)
        total_points += pts
        all_flags.extend(flg)
        all_details["html"] = det

    # text quality
    pts, flg, det = _text_signals(text)
    total_points += pts
    all_flags.extend(flg)
    all_details["text"] = det

    # semantic relevance to query
    relevance_score = 0.0
    if query:
        from lib.relevance import relevance
        relevance_score = relevance(query, text)
        all_details["relevance"] = round(relevance_score, 3)
        words = len(text.split())
        if relevance_score < relevance_thresholds.off_topic and words > 200:
            return {
                "score": 0, "flags": all_flags + ["off_topic"],
                "details": all_details, "page_type": ptype, "relevance": round(relevance_score, 3),
            }
        elif relevance_score >= relevance_thresholds.high:
            total_points += 15
            all_flags.append("highly_relevant")
        elif relevance_score >= relevance_thresholds.moderate:
            total_points += 8
            all_flags.append("relevant")
        elif relevance_score < relevance_thresholds.low and words > 200:
            total_points -= 15
            all_flags.append("low_relevance")

    score_val = max(0, min(100, total_points))
    return {
        "score": score_val, "flags": all_flags,
        "details": all_details, "page_type": ptype, "relevance": round(relevance_score, 3),
    }
