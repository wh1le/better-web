"""AI-generated content detection via zippy."""

try:
    from zippy.zippy import EnsembledZippy
    _zippy = EnsembledZippy()

    def ai_score(text: str) -> float:
        """Return 1.0 if AI-detected, 0.0 if human."""
        try:
            label, _conf = _zippy.run_on_text_chunked(text)
            return 1.0 if label == "AI" else 0.0
        except Exception:
            return 0.0
except ImportError:
    def ai_score(_text: str) -> float:  # type: ignore[misc]
        return 0.0
