"""Container entry point: ``python -m flowguard.serve``.

1. validate the environment (``flowguard.settings``); on error log one line and exit with status 2;
2. configure JSON logging with the environment and release on every line;
3. build the app and run uvicorn on 0.0.0.0:FLOWGUARD_PORT *inside the container* (the host decides
   what, if anything, is published: the course's scripts publish on 127.0.0.1 only).
"""
from __future__ import annotations

import logging
import os
import sys

import uvicorn

from flowguard import __version__, logs
from flowguard.api import create_app
from flowguard.settings import SettingsError, load_settings


def main() -> int:
    try:
        settings = load_settings(os.environ)
    except SettingsError as exc:
        logs.configure("INFO")
        logging.getLogger("flowguard.serve").error("invalid configuration: %s", exc,
                                                   extra={"event": "config_invalid"})
        return 2
    logs.configure(settings.log_level, context={"env": settings.environment, "release": settings.release})
    log = logging.getLogger("flowguard.serve")
    log.info("starting flowguard %s", __version__, extra={"event": "starting", "model_dir": settings.model_dir,
                                                         "port": settings.port})
    app = create_app(settings.model_dir, release=settings.release, environment=settings.environment)
    uvicorn.run(app, host="0.0.0.0", port=settings.port, log_config=None, access_log=True)  # noqa: S104
    return 0


if __name__ == "__main__":
    sys.exit(main())
