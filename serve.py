#!/usr/bin/env python3
"""Serve the start page on loopback, so it has an address of its own.

    python3 serve.py [port]          default 9875; `install.py --serve` sets it up at login

Opened as a file the page works fine, but to another program on your machine it is nobody: its
requests say they come from "null", and so do those of a sandboxed frame on any website. A local
service that should answer the page and no one else (what is playing, the lamp's audio) needs a
name to check, and http://127.0.0.1:9875 is one.

Only the page gets its own files. A request from another site is refused (your config.js would
otherwise be readable by any page that includes it as a script), and so is one that reached this
port under another name, anything starting with a dot, and folder listings.
"""
import argparse, functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

HERE = Path(__file__).resolve().parent


class Handler(SimpleHTTPRequestHandler):
    def allowed(self):
        port = self.server.server_address[1]
        if self.headers.get("Host") not in {f"{h}:{port}" for h in ("127.0.0.1", "localhost", "[::1]")}:
            return False
        # Firefox, Chrome and Safari say where a request comes from: "none" is you (the address
        # bar, a new tab), "same-origin" is the page itself. A browser too old to say is let in.
        if self.headers.get("Sec-Fetch-Site", "none") not in ("none", "same-origin"):
            return False
        return not any(part.startswith(".") for part in unquote(urlparse(self.path).path).split("/"))

    def do_GET(self):
        if not self.allowed():
            return self.send_error(403)
        super().do_GET()

    def do_HEAD(self):
        if not self.allowed():
            return self.send_error(403)
        super().do_HEAD()

    def list_directory(self, path):
        self.send_error(403)

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")  # news.js changes every 20 minutes: always ask
        super().end_headers()

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("port", type=int, nargs="?", default=9875)
    a = ap.parse_args()
    with ThreadingHTTPServer(("127.0.0.1", a.port), functools.partial(Handler, directory=str(HERE))) as httpd:
        print(f"serving {HERE} on http://127.0.0.1:{a.port}/", flush=True)
        httpd.serve_forever()
