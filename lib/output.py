"""File output, paths, slugification."""
import json
import os
import re

from lib.logging import done
from lib.settings import settings

SEARCH_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def slugify(text: str) -> str:
    max_length = settings.output.max_slug_length
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')[:max_length]


def output_path(mode: str, query: str) -> str:
    os.makedirs(SEARCH_DIR, exist_ok=True)
    return f"{SEARCH_DIR}/{mode}-{slugify(query)}.json"


def save(data: dict, out_file: str):
    os.makedirs(SEARCH_DIR, exist_ok=True)
    with open(out_file, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    done(f"Saved: {out_file}")
