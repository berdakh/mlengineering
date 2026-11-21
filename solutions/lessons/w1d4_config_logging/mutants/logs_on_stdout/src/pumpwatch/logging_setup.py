"""Logging configuration. Called exactly once, by the entry point (cli.main).

Library modules never call this; they only do ``logger = logging.getLogger(__name__)``.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

LOG_FORMAT = "%(asctime)s %(levelname)-7s %(name)s | %(message)s"


def setup_logging(level: str = "INFO", log_file: Path | None = None) -> None:
    """Send ``pumpwatch.*`` records to stderr (at ``level``) and to ``log_file`` (at DEBUG).

    stdout is reserved for the program's result (JSON), so that
    ``pumpwatch train ... | jq`` keeps working whatever the log level.
    Handlers are attached to the package logger, not the root logger, so
    third-party libraries stay quiet unless the application opts in.
    """
    logger = logging.getLogger("pumpwatch")
    for handler in list(logger.handlers):   # idempotent: safe to call again (tests, notebooks)
        logger.removeHandler(handler)
        handler.close()
    logger.setLevel(logging.DEBUG)          # handlers do the filtering
    logger.propagate = False

    formatter = logging.Formatter(LOG_FORMAT)
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console.setFormatter(formatter)
    logger.addHandler(console)

    if log_file is not None:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
