"""Load config.toml and lists.toml settings."""
import os
import tomllib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(ROOT, "config.toml")
LISTS_PATH = os.path.join(ROOT, "lists.toml")


def _load(path: str) -> dict:
    with open(path, "rb") as f:
        return tomllib.load(f)


_config: dict | None = None
_lists: dict | None = None


def get() -> dict:
    global _config
    if _config is None:
        _config = _load(CONFIG_PATH)
    return _config


def get_lists() -> dict:
    global _lists
    if _lists is None:
        _lists = _load(LISTS_PATH)
    return _lists
