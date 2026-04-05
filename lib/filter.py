"""URL and domain filtering — block low-value sites before scraping."""
import glob
import os
import re
import urllib.request

from lib.config import get as cfg, ROOT
from lib.logging import info, done

BLOCKLIST_DIR = os.path.join(ROOT, "data", "blocklists")


def _parse_ublacklist_line(line: str) -> str | None:
    """Extract domain from uBlacklist format lines like *://*.example.com/*"""
    line = line.strip()
    if not line or line.startswith("#") or line.startswith("!"):
        return None
    # match patterns like *://*.example.com/* or *://example.com/*
    m = re.match(r'\*://\*?\.?([a-z0-9][\w.-]+\.[a-z]{2,})(/\*)?$', line, re.IGNORECASE)
    if m:
        return m.group(1).lower()
    # plain domain
    m = re.match(r'^([a-z0-9][\w.-]+\.[a-z]{2,})$', line, re.IGNORECASE)
    if m:
        return m.group(1).lower()
    return None


def _load_blocklist_file(path: str) -> set[str]:
    domains = set()
    try:
        with open(path) as f:
            for line in f:
                d = _parse_ublacklist_line(line)
                if d:
                    domains.add(d)
    except FileNotFoundError:
        pass
    return domains


def _load_all_blocklists() -> set[str]:
    domains = set()
    # downloaded lists
    for f in glob.glob(os.path.join(BLOCKLIST_DIR, "*.txt")):
        domains |= _load_blocklist_file(f)
    # custom blocked from config
    config = cfg()
    for d in config.get("blocklists", {}).get("custom_blocked", []):
        domains.add(d.lower())
    return domains


_blocked: set[str] | None = None


def blocked_domains() -> set[str]:
    global _blocked
    if _blocked is None:
        _blocked = _load_all_blocklists()
    return _blocked


def domain_from_url(url: str) -> str:
    try:
        domain = url.split("//")[1].split("/")[0].lower()
        return re.sub(r'^www\.', '', domain)
    except (IndexError, AttributeError):
        return ""


def is_blocked(url: str) -> bool:
    domain = domain_from_url(url)
    blocked = blocked_domains()
    # exact match
    if domain in blocked:
        return True
    # subdomain match
    parts = domain.split(".")
    for i in range(1, len(parts)):
        parent = ".".join(parts[i:])
        if parent in blocked:
            return True
    return False


def update_blocklists():
    """Download all blocklist sources from config."""
    os.makedirs(BLOCKLIST_DIR, exist_ok=True)
    config = cfg()
    sources = config.get("blocklists", {}).get("sources", [])

    for src in sources:
        name = src["name"]
        url = src["url"]
        out = os.path.join(BLOCKLIST_DIR, f"{name}.txt")
        info(f"Downloading {name}...")
        try:
            urllib.request.urlretrieve(url, out)
            # count domains
            domains = _load_blocklist_file(out)
            done(f"  {name}: {len(domains)} domains")
        except Exception as e:
            info(f"  Failed: {e}")

    # reset cache
    global _blocked
    _blocked = None
    total = len(blocked_domains())
    done(f"Total: {total} blocked domains")
