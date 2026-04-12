"""Content deduplication using MinHash LSH."""
from datasketch import MinHashLSH

from lib.logging import info, step
from lib.settings import settings
from lib.shingling import minhash, shingle


def deduplicate(entries: list[dict]) -> list[dict]:
    """Remove near-duplicate entries based on content similarity.

    Keeps the highest quality version of duplicates.
    """
    step("Dedup")
    if not entries:
        info("[dim]nothing to deduplicate[/dim]")
        return entries

    dedup_settings = settings.dedup

    # sort by quality so we keep the best version of duplicates
    entries_sorted = sorted(
        entries,
        key=lambda entry: entry.get("quality", {}).get("score", 50),
        reverse=True,
    )

    lsh = MinHashLSH(threshold=dedup_settings.threshold, num_perm=dedup_settings.num_perm)
    kept = []
    seen_keys = set()

    for entry in entries_sorted:
        content = entry.get("content") or ""
        if len(content) < dedup_settings.min_content_length:
            kept.append(entry)
            continue

        shingles = shingle(content, dedup_settings.shingle_size)
        mh = minhash(shingles, dedup_settings.num_perm)

        key = entry.get("url", str(id(entry)))
        try:
            matches = lsh.query(mh)
        except ValueError:
            matches = []

        if matches:
            if "quality" not in entry:
                entry["quality"] = {}
            entry["quality"].setdefault("flags", []).append("near_duplicate")
            continue

        try:
            lsh.insert(key, mh)
            seen_keys.add(key)
        except ValueError:
            pass
        kept.append(entry)

    removed = len(entries_sorted) - len(kept)
    if removed:
        info(f"[dim]dropped {removed} near-duplicates, {len(kept)} remain[/dim]")
    else:
        info(f"[dim]no duplicates across {len(kept)} pages[/dim]")

    return kept
