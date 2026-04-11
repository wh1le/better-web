"""Semantic relevance scoring: query vs page content using sentence-transformers."""
import os
import warnings

from lib.settings import ROOT, settings

os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")  # must be set before HF imports
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
warnings.filterwarnings("ignore", message=".*unauthenticated.*")  # noqa: E402


class RelevanceScorer:
    """Score how relevant text is to a query using sentence-transformers."""

    def __init__(self):
        self._model = None

    def score(self, query: str, text: str) -> float:
        """Score how relevant text is to a query. Returns 0.0 to 1.0."""
        if not query or not text:
            return 0.0

        model = self._get_model()
        max_chars = settings.models.embedding_max_chars
        text_trimmed = text[:max_chars]

        embeddings = model.encode([query, text_trimmed], normalize_embeddings=True)
        similarity = float(embeddings[0] @ embeddings[1])

        return max(0.0, min(1.0, similarity))

    def _get_model(self):
        if self._model is None:
            import logging
            for name in ("sentence_transformers", "transformers", "huggingface_hub", "safetensors"):
                logging.getLogger(name).setLevel(logging.ERROR)
            from sentence_transformers import SentenceTransformer
            model_name = settings.models.embedding
            self._model = SentenceTransformer(model_name, cache_folder=os.path.join(ROOT, "models"))
        return self._model


scorer = RelevanceScorer()
