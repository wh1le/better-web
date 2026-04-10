"""Settings: Dynaconf for config, .txt/.yaml files for static data."""
from __future__ import annotations

from functools import cached_property
from pathlib import Path

import yaml
from dynaconf import Dynaconf

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.yaml"
DATA_DIR = ROOT / "data"


class Settings:
    """Central access to config values and static data lists."""

    def __init__(self, path: str = str(CONFIG_PATH), data_dir: Path = DATA_DIR) -> None:
        self._config = Dynaconf(
            settings_files=[path],
            environments=False,
            lowercase_read=True,
        )
        self._data_dir = data_dir

    @property
    def config(self) -> Dynaconf:
        return self._config

    def __getattr__(self, name: str) -> object:
        return getattr(self._config, name)

    # --- static lists ---

    @cached_property
    def skip_extensions(self) -> set[str]:
        return set(self._load_list("skip_extensions"))

    @cached_property
    def high_quality_tlds(self) -> set[str]:
        return set(self._load_list("high_quality_tlds"))

    @cached_property
    def low_quality_tlds(self) -> set[str]:
        return set(self._load_list("low_quality_tlds"))

    @cached_property
    def seo_keywords(self) -> set[str]:
        return set(self._load_list("seo_keywords"))

    @cached_property
    def ai_phrases(self) -> list[str]:
        return self._load_list("ai_phrases")

    @cached_property
    def discussion_markers(self) -> list[str]:
        return self._load_list("discussion_markers")

    @cached_property
    def custom_blocked(self) -> list[str]:
        return self._load_list("custom_blocked")

    @cached_property
    def ad_trackers(self) -> list[str]:
        return self._load_list("ad_trackers")

    @cached_property
    def page_types(self) -> dict[str, list[str]]:
        return self._load_yaml("page_types")

    @cached_property
    def url_rewrites(self) -> dict[str, str]:
        return self._load_yaml("url_rewrites")

    @cached_property
    def blocklists(self) -> list[dict[str, object]]:
        return list(self._config.blocklists)

    # --- private ---

    def _load_list(self, name: str) -> list[str]:
        path = self._data_dir / f"{name}.txt"
        return [
            line.strip() for line in path.read_text().splitlines()
            if line.strip() and not line.startswith("#")
        ]

    def _load_yaml(self, name: str) -> dict:
        path = self._data_dir / f"{name}.yaml"
        with path.open() as f:
            return yaml.safe_load(f)


settings = Settings()
