"""Service configuration from environment variables, validated once at startup. YOU IMPLEMENT
``load_settings`` (w6d6, task 3).

Twelve-factor style: the image is identical in every environment; only the environment differs.
``load_settings`` turns a mapping of environment variables into a frozen ``Settings`` object or
raises ``SettingsError`` whose message names the offending variable. ``flowguard.serve`` calls it
before anything else and exits with status 2 on error, so a misconfigured container stops at once
with one clear log line instead of serving with a silently wrong setting.

Variables (all start with ``FLOWGUARD_``; any other ``FLOWGUARD_*`` name is an error, which catches
typos such as ``FLOWGUARD_MODEL_DlR``):

=====================  ========  ==========================================================
FLOWGUARD_ENV          required  one of: local, staging, production
FLOWGUARD_MODEL_DIR    required  absolute path to the model bundle directory
FLOWGUARD_RELEASE      required  the image's release id: 7-40 lowercase hex characters (git SHA)
FLOWGUARD_LOG_LEVEL    optional  DEBUG, INFO, WARNING or ERROR (default INFO)
FLOWGUARD_PORT         optional  integer 1-65535 (default 8000)
=====================  ========  ==========================================================

Validation checks format, not existence: whether the bundle at FLOWGUARD_MODEL_DIR exists and is
intact is the readiness probe's job (``/readyz``), so the container keeps running and keeps
logging while it is not ready.
"""
from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

PREFIX = "FLOWGUARD_"
ENVIRONMENTS = ("local", "staging", "production")
LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR")
KNOWN = ("FLOWGUARD_ENV", "FLOWGUARD_MODEL_DIR", "FLOWGUARD_RELEASE", "FLOWGUARD_LOG_LEVEL", "FLOWGUARD_PORT")
_RELEASE = re.compile(r"^[0-9a-f]{7,40}$")


class SettingsError(ValueError):
    """A configuration problem; the message names the environment variable."""


@dataclass(frozen=True)
class Settings:
    environment: str
    model_dir: str
    release: str
    log_level: str = "INFO"
    port: int = 8000


def load_settings(env: Mapping[str, str]) -> Settings:
    """Validate the ``FLOWGUARD_*`` variables of ``env`` (e.g. ``os.environ``) and return ``Settings``.

    TODO (task 3). Raise ``SettingsError`` whose message contains the variable's name when:
      * a FLOWGUARD_* variable is not one of KNOWN (catches typos);
      * a required variable is missing or empty;
      * FLOWGUARD_ENV is not in ENVIRONMENTS; FLOWGUARD_MODEL_DIR is not absolute;
        FLOWGUARD_RELEASE is not 7-40 lowercase hex; FLOWGUARD_LOG_LEVEL is not in LOG_LEVELS
        (accept lower case input, store upper case); FLOWGUARD_PORT is not an integer in 1-65535.
    Defaults: log level INFO, port 8000. Variables without the FLOWGUARD_ prefix are ignored.
    """
    raise NotImplementedError
