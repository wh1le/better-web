"""Extract clean text from research JSON for LLM consumption."""
import glob
import json
import os

from .output import SEARCH_DIR
from .settings import settings


def find_latest() -> str | None:
    files = sorted(glob.glob(os.path.join(SEARCH_DIR, "*.json")), key=os.path.getmtime)
    return files[-1] if files else None


def _tier(quality_score: int) -> str:
    tiers = settings.output.tiers
    if quality_score >= tiers.high:
        return "HIGH"
    if quality_score >= tiers.med:
        return "MED"
    return "LOW"


def digest(path: str) -> str:
    output = settings.output

    with open(path) as f:
        data = json.load(f)

    query = data.get("query") or ", ".join(data.get("queries", []))
    log = data.get("log", {})

    # filter by length + quality, sort best first
    usable = [
        result for result in data["results"]
        if len(result.get("content") or "") >= output.min_length
        and result.get("quality", {}).get("score", 50) >= output.min_score
    ]
    usable.sort(
        key=lambda result: (
            result.get("quality", {}).get("score", 50)
            * max(result.get("quality", {}).get("relevance", 0.5), 0.1)
        ),
        reverse=True,
    )

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

    for result in usable:
        content = result["content"]
        quality = result.get("quality", {})
        quality_score = quality.get("score", 50)
        relevance_score = quality.get("relevance", 0.0)
        page_type = quality.get("page_type", "unknown")

        # cap content per page
        if len(content) > output.max_chars:
            content = content[:output.max_chars] + settings.output.truncation_marker

        tier = _tier(quality_score)
        header = f"## [{tier}] {result['title']}"
        score_line = f"quality: {quality_score}/100 | relevance: {relevance_score} | type: {page_type}"

        parts.append(header)
        parts.append(score_line)
        parts.append(content)
        parts.append("")

    return "\n\n".join(parts)


def stats(path: str) -> dict:
    output = settings.output

    with open(path) as f:
        data = json.load(f)

    query = data.get("query") or ", ".join(data.get("queries", []))
    good = [
        result for result in data["results"]
        if result.get("content") and len(result["content"]) > output.min_length
        and result.get("quality", {}).get("score", 50) >= output.min_score
    ]
    low_quality = sum(
        1 for result in data["results"]
        if result.get("content") and len(result["content"]) > output.min_length
        and result.get("quality", {}).get("score", 50) < output.min_score
    )
    chars = sum(min(len(result["content"]), output.max_chars) for result in good)

    return {
        "file": os.path.basename(path),
        "query": query,
        "total": len(data["results"]),
        "usable": len(good),
        "filtered": low_quality,
        "chars": chars,
        "tokens": chars // settings.output.tokens_per_char,
    }
