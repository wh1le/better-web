"""Load config.toml settings."""
import os

try:
    import tomllib
except ImportError:
    import tomli as tomllib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(ROOT, "config.toml")


def load() -> dict:
    with open(CONFIG_PATH, "rb") as f:
        return tomllib.load(f)


_config = None


def get() -> dict:
    global _config
    if _config is None:
        _config = load()
    return _config
