"""One JSON object per log line, on stdout, so a container platform can collect and query them.

Every line has ``ts`` (UTC, ISO 8601), ``level``, ``logger`` and ``msg``; fields passed through
``extra={...}`` are added as top-level keys, and the static ``context`` given to ``configure``
(environment, release) is added to every line. Exceptions are logged as a single-line ``exc`` field.
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone

_STANDARD = set(vars(logging.LogRecord("", 0, "", 0, "", None, None))) | {"message", "asctime", "taskName", "color_message"}


class JsonFormatter(logging.Formatter):
    def __init__(self, context: dict | None = None):
        super().__init__()
        self.context = dict(context or {})

    def format(self, record: logging.LogRecord) -> str:
        line = {"ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(timespec="milliseconds"),
                "level": record.levelname, "logger": record.name, "msg": record.getMessage(), **self.context}
        for key, value in vars(record).items():
            if key not in _STANDARD and not key.startswith("_"):
                line[key] = value
        if record.exc_info:
            line["exc"] = self.formatException(record.exc_info).replace("\n", " | ")
        return json.dumps(line, default=str)


def configure(level: str = "INFO", context: dict | None = None) -> None:
    """Route every logger (including uvicorn's) through one JSON handler on stdout."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter(context))
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level)
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        lg.handlers[:] = []
        lg.propagate = True
