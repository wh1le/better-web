"""URL and domain filtering — block low-value sites before scraping."""
import glob
import os
import re
import urllib.request

from lib.logging import done, info
from lib.settings import ROOT, settings

BLOCKLIST_DIR = os.path.join(ROOT, "output", "blocklists")


def _parse_ublacklist_line(line: str) -> str | None:
    """Extract domain from uBlacklist format lines like *://*.example.com/*"""
    line = line.strip()
    if not line or line.startswith("#") or line.startswith("!"):
        return None
    match = re.match(r'\*://\*?\.?([a-z0-9][\w.-]+\.[a-z]{2,})(/\*)?$', line, re.IGNORECASE)
    if match:
        return match.group(1).lower()
    match = re.match(r'^([a-z0-9][\w.-]+\.[a-z]{2,})$', line, re.IGNORECASE)
    if match:
        return match.group(1).lower()
    return None


def _load_blocklist_file(path: str) -> set[str]:
    domains = set()
    try:
        with open(path) as f:
            for line in f:
                domain = _parse_ublacklist_line(line)
                if domain:
                    domains.add(domain)
    except FileNotFoundError:
        pass
    return domains


def _load_all_blocklists() -> set[str]:
    domains = set()
    for filepath in glob.glob(os.path.join(BLOCKLIST_DIR, "*.txt")):
        domains |= _load_blocklist_file(filepath)
    for domain in settings.custom_blocked:
        domains.add(domain.lower())
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
    if domain in blocked:
        return True
    parts = domain.split(".")
    for i in range(1, len(parts)):
        parent = ".".join(parts[i:])
        if parent in blocked:
            return True
    return False


def update_blocklists():
    """Download all blocklist sources from config."""
    os.makedirs(BLOCKLIST_DIR, exist_ok=True)

    for source in settings.blocklists:
        name = source["name"]
        url = source["url"]
        out = os.path.join(BLOCKLIST_DIR, f"{name}.txt")
        info(f"Downloading {name}...")
        try:
            urllib.request.urlretrieve(url, out)
            domains = _load_blocklist_file(out)
            done(f"  {name}: {len(domains)} domains")
        except Exception as err:
            info(f"  Failed: {err}")

    global _blocked
    _blocked = None
    total = len(blocked_domains())
    done(f"Total: {total} blocked domains")
