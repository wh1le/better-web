"""URL and domain filtering — block low-value sites before scraping."""
import glob
import os
import re
import urllib.request

from lib.logging import done, info
from lib.settings import ROOT, settings

BLOCKLIST_DIR = os.path.join(ROOT, "output", "blocklists")


class DomainFilter:
    """Loads and checks domains against blocklists."""

    def __init__(self):
        self._blocked = self._load_all()

    def is_blocked(self, url: str) -> bool:
        domain = self._domain_from_url(url)
        if domain in self._blocked:
            return True
        parts = domain.split(".")
        for i in range(1, len(parts)):
            parent = ".".join(parts[i:])
            if parent in self._blocked:
                return True
        return False

    def update(self):
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

        self._blocked = self._load_all()
        done(f"Total: {len(self._blocked)} blocked domains")

    def _load_all(self) -> set[str]:
        domains = set()
        for filepath in glob.glob(os.path.join(BLOCKLIST_DIR, "*.txt")):
            domains |= _load_blocklist_file(filepath)
        for domain in settings.custom_blocked:
            domains.add(domain.lower())
        return domains

    def _domain_from_url(self, url: str) -> str:
        try:
            domain = url.split("//")[1].split("/")[0].lower()
            return re.sub(r'^www\.', '', domain)
        except (IndexError, AttributeError):
            return ""


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


domain_filter = DomainFilter()
