import urllib.request

from lib.settings import settings


def check_searx() -> dict:
    base_url = settings.searx_engine.url.rsplit("/", 1)[0]
    try:
        req = urllib.request.Request(f"{base_url}/healthz", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return {"status": "ok", "url": base_url, "http_status": resp.status}
    except Exception as err:
        return {"status": "error", "url": base_url, "error": str(err)}
