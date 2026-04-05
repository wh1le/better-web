"""Extract clean text from research JSON for LLM consumption."""
import glob
import json
import os

from .output import SEARCH_DIR
from .config import get as cfg


def _digest_config():
    c = cfg().get("digest", {})
    return {
        "max_chars": c.get("max_chars_per_page", 3000),
        "min_length": c.get("min_content_length", 200),
        "min_quality": c.get("min_quality_score", 30),
    }


def find_latest() -> str | None:
    files = sorted(glob.glob(os.path.join(SEARCH_DIR, "*.json")), key=os.path.getmtime)
    return files[-1] if files else None


def _tier(score: int) -> str:
    if score >= 70:
        return "HIGH"
    if score >= 45:
        return "MED"
    return "LOW"


def digest(path: str) -> str:
    dc = _digest_config()
    with open(path) as f:
        data = json.load(f)

    query = data.get("query") or ", ".join(data.get("queries", []))
    log = data.get("log", {})

    # filter by length + quality, sort best first
    min_q = dc["min_quality"]
    usable = [
        r for r in data["results"]
        if len(r.get("content") or "") >= dc["min_length"]
        and r.get("quality", {}).get("score", 50) >= min_q
    ]
    usable.sort(key=lambda r: r.get("quality", {}).get("score", 50) * max(r.get("quality", {}).get("relevance", 0.5), 0.1), reverse=True)

    total = len(data["results"])
    filtered = total - len(usable)
    dedup_removed = log.get("dedup_removed", 0)

    # header with context for the LLM
    parts = [f"# Research: {query}"]
    meta = [f"{len(usable)} sources"]
    if filtered:
        meta.append(f"{filtered} low-quality filtered out")
    if dedup_removed:
        meta.append(f"{dedup_removed} near-duplicates removed")
    parts.append(f"_Scored and ranked by content quality. {', '.join(meta)}._\n")

    for i, r in enumerate(usable, 1):
        content = r["content"]
        q = r.get("quality", {})
        q_score = q.get("score", 50)
        relevance = q.get("relevance", 0.0)
        page_type = q.get("page_type", "unknown")
        domain = q.get("details", {}).get("domain", {}).get("domain", "")

        # cap content per page
        if len(content) > dc["max_chars"]:
            content = content[:dc["max_chars"]] + "\n[...truncated]"

        tier = _tier(q_score)
        header = f"## [{tier}] {r['title']}"
        meta_line = f"source: {r['url']}"
        score_line = f"quality: {q_score}/100 | relevance: {relevance} | type: {page_type}"

        parts.append(header)
        parts.append(score_line)
        parts.append(content)
        parts.append("")

    return "\n\n".join(parts)


def stats(path: str) -> dict:
    dc = _digest_config()
    with open(path) as f:
        data = json.load(f)

    query = data.get("query") or ", ".join(data.get("queries", []))
    min_q = dc["min_quality"]
    good = [
        r for r in data["results"]
        if r.get("content") and len(r["content"]) > dc["min_length"]
        and r.get("quality", {}).get("score", 50) >= min_q
    ]
    low_quality = sum(
        1 for r in data["results"]
        if r.get("content") and len(r["content"]) > dc["min_length"]
        and r.get("quality", {}).get("score", 50) < min_q
    )
    chars = sum(min(len(r["content"]), dc["max_chars"]) for r in good)

    return {
        "file": os.path.basename(path),
        "query": query,
        "total": len(data["results"]),
        "usable": len(good),
        "filtered": low_quality,
        "chars": chars,
        "tokens": chars // 4,
    }
