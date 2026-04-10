"""MinHash shingling for content deduplication."""
from datasketch import MinHash


def shingle(text: str, shingle_size: int) -> set[str]:
    """Create k-shingles (character n-grams) from text."""
    text = text.lower().strip()
    if len(text) < shingle_size:
        return {text}
    return {text[i:i + shingle_size] for i in range(len(text) - shingle_size + 1)}


def minhash(shingles: set[str], num_perm: int) -> MinHash:
    """Create a MinHash from a set of shingles."""
    mh = MinHash(num_perm=num_perm)
    for s in shingles:
        mh.update(s.encode("utf-8"))
    return mh
