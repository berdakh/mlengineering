"""Start the flowguard API with N worker processes and TCP_NODELAY on every connection (given).

    python labs/w6d4_latency_resources/lab/serve.py --workers 2 [--host 127.0.0.1] [--port 8000]

Why this file exists (lesson w6d4, section 4, task 6). With `uvicorn --workers N` (N > 1), uvicorn 0.54
creates the shared listening socket as `socket.socket(family=AF_INET)`, whose protocol number is 0.
asyncio turns on TCP_NODELAY for a connection only when the socket's protocol number is IPPROTO_TCP,
so in multi-worker mode Nagle's algorithm stays on, and responses that are written in more than one
piece wait for the client's delayed ACK (about 40 ms on Linux). Measured in the lesson: median latency
about 52 ms with 2 workers against about 10 ms with 1 worker, at the same request rate.
Here the socket is created with IPPROTO_TCP explicitly, so asyncio sets TCP_NODELAY as usual.

Uses `uvicorn.supervisors.Multiprocess`, which is importable but not a documented public API: pin the
uvicorn version, and re-check this behaviour when you upgrade (the measurement in the lesson is the test).
"""
from __future__ import annotations

import argparse
import os
import socket
import sys
from pathlib import Path

import uvicorn
from uvicorn.supervisors import Multiprocess

HERE = Path(__file__).resolve().parent


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--log-level", default="warning")
    args = ap.parse_args(argv)
    os.environ.setdefault("FLOWGUARD_MODEL_DIR", str(HERE / "models" / "flowguard-z" / "1.0.0"))
    config = uvicorn.Config("flowguard.api:create_app_from_env", factory=True, host=args.host, port=args.port,
                            workers=args.workers, log_level=args.log_level)
    if args.workers == 1:
        uvicorn.Server(config).run()
        return 0
    family = socket.AF_INET6 if ":" in args.host else socket.AF_INET
    sock = socket.socket(family, socket.SOCK_STREAM, socket.IPPROTO_TCP)   # protocol number set explicitly
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((args.host, args.port))
    Multiprocess(config, sockets=[sock]).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
