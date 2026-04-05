"""Content-level deduplication using MinHash LSH (datasketch)."""
from datasketch import MinHash, MinHashLSH


def _shingle(text: str, k: int = 5) -> set[str]:
    """Create k-shingles (character n-grams) from text."""
    text = text.lower().strip()
    return {text[i:i + k] for i in range(len(text) - k + 1)} if len(text) >= k else {text}


def _minhash(shingles: set[str], num_perm: int = 128) -> MinHash:
    m = MinHash(num_perm=num_perm)
    for s in shingles:
        m.update(s.encode("utf-8"))
    return m


def deduplicate(entries: list[dict], threshold: float = 0.6) -> list[dict]:
    """Remove near-duplicate entries based on content similarity.

    Args:
        entries: list of result dicts with "content" key
        threshold: Jaccard similarity threshold (0.6 = 60% similar → duplicate)

    Returns:
        entries with near-duplicates removed (keeps highest quality version)
    """
    if not entries:
        return entries

    # sort by quality so we keep the best version of duplicates
    entries_sorted = sorted(
        entries,
        key=lambda e: e.get("quality", {}).get("score", 50),
        reverse=True,
    )

    lsh = MinHashLSH(threshold=threshold, num_perm=128)
    kept = []
    seen_keys = set()

    for entry in entries_sorted:
        content = entry.get("content") or ""
        if len(content) < 100:
            kept.append(entry)
            continue

        shingles = _shingle(content)
        mh = _minhash(shingles)

        # check for near-duplicates
        key = entry.get("url", str(id(entry)))
        try:
            matches = lsh.query(mh)
        except ValueError:
            matches = []

        if matches:
            # this is a near-duplicate of something we already kept
            if "quality" not in entry:
                entry["quality"] = {}
            entry["quality"].setdefault("flags", []).append("near_duplicate")
            continue

        # no match — keep it and index it
        try:
            lsh.insert(key, mh)
            seen_keys.add(key)
        except ValueError:
            pass  # duplicate key, skip
        kept.append(entry)

    return kept
