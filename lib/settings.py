"""Typed settings from config.toml + lists.toml with dot access."""
from __future__ import annotations

from typing import Any

from lib.config import get as _cfg
from lib.config import get_lists as _lists


class Section:
    """Turn a dict into dot-accessible attributes."""

    def __init__(self, data: dict):
        for key, val in data.items():
            setattr(self, key, Section(val) if isinstance(val, dict) else val)

    def __getattr__(self, name: str) -> Any:
        raise AttributeError(f"Setting '{name}' not found")

    def __repr__(self):
        return f"Section({vars(self)})"


def _merge(base: dict, override: dict) -> dict:
    """Deep merge override into base."""
    out = dict(base)
    for k, v in override.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


DEFAULTS = {
    "searx_engine": {
        "url": "http://localhost:8882/search",
        "max_pages": 20,
        "delay": 1.0,
    },
    "scrape": {
        "timeout": 10000,
        "batch": [2, 4],
        "delay": [1.0, 3.0],
        "backoff": [3.0, 6.0],
    },
    "scoring": {
        "baseline": 50,
        "ai_penalty": -20,
        "min_text": 50,
        "relevance": {"off_topic": 0.15, "low": 0.2, "moderate": 0.3, "high": 0.5},
    },
    "output": {
        "max_chars": 12000,
        "min_length": 200,
        "min_score": 30,
        "max_slug_length": 80,
        "tokens_per_char": 4,
        "truncation_marker": "\n[...truncated]",
        "tiers": {"high": 70, "med": 45},
    },
    "models": {
        "embedding": "all-MiniLM-L6-v2",
        "embedding_max_chars": 5000,
        "whisper": "base",
        "whisper_device": "cpu",
        "whisper_compute_type": "int8",
        "whisper_audio_format": "bestaudio/best",
    },
    "dedup": {
        "threshold": 0.6,
        "shingle_size": 5,
        "num_perm": 128,
        "min_content_length": 100,
    },
    "llm": {
        "model_path": "models/model.gguf",
        "context_length": 2048,
        "max_tokens": 512,
        "max_input_chars": 4000,
        "temperature": 0.1,
        "threads": 4,
    },
}

LIST_DEFAULTS = {
    "skip_extensions": [".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx", ".zip", ".tar", ".gz"],
    "high_quality_tlds": ["edu", "gov", "mil", "ac.uk", "gov.uk", "edu.au"],
    "low_quality_tlds": ["xyz", "click", "top", "buzz", "site", "online", "store",
                         "club", "icu", "fun", "wang", "gdn", "bid", "loan", "racing"],
    "seo_keywords": ["best", "top", "review", "guide", "tips", "ultimate", "cheap", "deals", "coupon"],
    "slop_phrases": [
        "it's important to note", "it is important to note",
        "in this article", "let's dive", "dive into",
        "in today's digital", "whether you're a",
        "in conclusion", "game changer", "game-changer",
        "comprehensive guide", "everything you need to know",
        "look no further", "without further ado",
        "in the world of", "navigating the",
        "at the end of the day", "it's worth noting",
        "unlock the power", "the ultimate guide",
        "streamline your", "take it to the next level",
        "leverage the power", "delve into",
    ],
    "discussion_markers": ["replied", "says ", "wrote:", "commented", "points)", "upvote"],
    "blocklists": [],
    "custom_blocked": [],
}


def load() -> Section:
    """Load config.toml + lists.toml, merge with defaults, return as dot-access object."""
    merged = _merge(DEFAULTS, _cfg())
    lists = _merge(LIST_DEFAULTS, _lists())

    # convert to sets for fast lookup
    for key in ("high_quality_tlds", "low_quality_tlds", "seo_keywords"):
        lists[key] = set(lists[key])

    merged["lists"] = lists
    return Section(merged)


settings = load()
