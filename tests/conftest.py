import json
import os
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

import pytest
import vcr

CASSETTES_DIR = os.path.join(os.path.dirname(__file__), "cassettes")
FIXTURES_DIR = Path(__file__).parent / "fixtures"
RECORD_MODE = "once" if os.environ.get("VCR_RECORD") else "none"
REPLAY_HOST = "127.0.0.1"
REPLAY_PORT = 18932
REPLAY_BASE = f"http://{REPLAY_HOST}:{REPLAY_PORT}"
SEARX_SCRUB = "http://searx:8888/search"


def _scrub_searx_request(request):
    request.uri = request.uri.replace("localhost:8882", "searx:8888")
    if "Host" in request.headers:
        request.headers["Host"] = ["searx:8888"]
    return request


search_vcr = vcr.VCR(
    cassette_library_dir  = CASSETTES_DIR,
    record_mode           = RECORD_MODE,
    before_record_request = _scrub_searx_request,
)

# --- local HTML server for crawl4ai replay ---

_html_pages = {}


class _ReplayHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        html = _html_pages.get(self.path)
        if html:
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(html.encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *args):
        pass


class _ReusableHTTPServer(HTTPServer):
    allow_reuse_address = True
    allow_reuse_port = True


@pytest.fixture(scope="session", autouse=True)
def replay_server():
    if os.environ.get("VCR_RECORD"):
        yield None
        return
    server = _ReusableHTTPServer((REPLAY_HOST, REPLAY_PORT), _ReplayHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server
    server.shutdown()


def load_html_fixtures(name):
    path = FIXTURES_DIR / f"{name}.json"
    if not path.exists():
        return {}
    with path.open() as f:
        entries = json.load(f)
    url_map = {}
    for entry in entries:
        if entry.get("html"):
            _html_pages[entry["path"]] = entry["html"]
            url_map[entry["url"]] = f"{REPLAY_BASE}{entry['path']}"
    return url_map


def save_html_fixtures(name, results):
    FIXTURES_DIR.mkdir(exist_ok=True)
    entries = []
    for i, r in enumerate(results):
        entries.append({
            "path": f"/page/{i}",
            "url": r["url"],
            "html": r.get("html"),
        })
    with (FIXTURES_DIR / f"{name}.json").open("w") as f:
        json.dump(entries, f)
