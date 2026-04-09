"""Content-level deduplication using MinHash LSH (datasketch)."""
from datasketch import MinHash, MinHashLSH

from lib.settings import settings


def _shingle(text: str) -> set[str]:
    """Create k-shingles (character n-grams) from text."""
    shingle_size = settings.dedup.shingle_size
    text = text.lower().strip()
    if len(text) < shingle_size:
        return {text}
    return {text[i:i + shingle_size] for i in range(len(text) - shingle_size + 1)}


def _minhash(shingles: set[str]) -> MinHash:
    mh = MinHash(num_perm=settings.dedup.num_perm)
    for shingle in shingles:
        mh.update(shingle.encode("utf-8"))
    return mh


def deduplicate(entries: list[dict]) -> list[dict]:
    """Remove near-duplicate entries based on content similarity.

    Keeps the highest quality version of duplicates.
    """
    if not entries:
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

        shingles = _shingle(content)
        mh = _minhash(shingles)

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

    return kept
