"""Semantic relevance scoring: query vs page content using sentence-transformers."""
import os
import warnings

os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
warnings.filterwarnings("ignore", message=".*unauthenticated.*")

from lib.config import ROOT

MODEL_NAME = "all-MiniLM-L6-v2"
MODEL_DIR = os.path.join(ROOT, "models", MODEL_NAME)

_model = None


def _get_model():
    global _model
    if _model is None:
        import logging
        # suppress HF/sentence-transformers loading noise
        for name in ("sentence_transformers", "transformers", "huggingface_hub", "safetensors"):
            logging.getLogger(name).setLevel(logging.ERROR)
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(MODEL_NAME, cache_folder=os.path.join(ROOT, "models"))
    return _model


def relevance(query: str, text: str, max_chars: int = 5000) -> float:
    """Score how relevant text is to a query. Returns 0.0 to 1.0."""
    if not query or not text:
        return 0.0

    model = _get_model()

    # truncate text to keep embedding fast
    text_trimmed = text[:max_chars]

    embeddings = model.encode([query, text_trimmed], normalize_embeddings=True)
    # cosine similarity of normalized vectors = dot product
    similarity = float(embeddings[0] @ embeddings[1])

    # clamp to 0-1
    return max(0.0, min(1.0, similarity))
