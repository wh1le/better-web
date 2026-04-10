"""Content quality scoring: composes domain, text, HTML, and AI signals."""
from lib.domain_scoring import domain_score, page_type
from lib.html_scoring import html_signals
from lib.settings import settings
from lib.text_scoring import text_signals


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
        pts, flg, det = domain_score(url)
        total_points += pts
        all_flags.extend(flg)
        all_details["domain"] = det

    # page type
    ptype = page_type(url) if url else "unknown"

    # HTML structure
    if html:
        pts, flg, det = html_signals(html, text)
        total_points += pts
        all_flags.extend(flg)
        all_details["html"] = det

    # text quality (includes AI detection)
    pts, flg, det = text_signals(text)
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
