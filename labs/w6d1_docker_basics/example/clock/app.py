"""A tiny JSON clock service, standard library only (w6d1 worked example).

    python app.py                     # serves http://0.0.0.0:8080/  (inside a container)
    GET /       -> {"time": "...", "uptime_s": ..., "pid": ...}
    GET /health -> {"status": "ok"}

SIGTERM handling is switchable so the example can show why it matters for a container's PID 1:
    CLOCK_HANDLE_SIGTERM=1 (default)  stop cleanly on SIGTERM
    CLOCK_HANDLE_SIGTERM=0            install no handler (Python's default action)
"""
from __future__ import annotations

import json
import os
import signal
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

STARTED = time.monotonic()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 (http.server naming)
        if self.path == "/health":
            body = {"status": "ok"}
        elif self.path == "/":
            body = {"time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "uptime_s": round(time.monotonic() - STARTED, 1), "pid": os.getpid()}
        else:
            self.send_error(404)
            return
        data = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):  # one line per request on stdout
        print(f"{self.address_string()} {fmt % args}", flush=True)


def main() -> int:
    host = os.environ.get("CLOCK_HOST", "0.0.0.0")
    port = int(os.environ.get("CLOCK_PORT", "8080"))
    server = ThreadingHTTPServer((host, port), Handler)
    if os.environ.get("CLOCK_HANDLE_SIGTERM", "1") == "1":
        def on_sigterm(signum, frame):
            print("SIGTERM received: shutting down", flush=True)
            threading.Thread(target=server.shutdown).start()   # shutdown() must not run in serve_forever's thread
        signal.signal(signal.SIGTERM, on_sigterm)
    print(f"clock listening on {host}:{port} as uid {os.getuid()}, pid {os.getpid()}", flush=True)
    server.serve_forever()
    server.server_close()
    print("stopped cleanly", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
