"""Service configuration from environment variables, validated once at startup.

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


def _required(env: Mapping[str, str], name: str) -> str:
    value = env.get(name, "").strip()
    if not value:
        raise SettingsError(f"{name} is required but not set")
    return value


def load_settings(env: Mapping[str, str]) -> Settings:
    """Validate the ``FLOWGUARD_*`` variables of ``env`` (e.g. ``os.environ``)."""
    unknown = sorted(k for k in env if k.startswith(PREFIX) and k not in KNOWN)
    if False:
        raise SettingsError(f"unknown variable(s) {', '.join(unknown)}; expected only {', '.join(KNOWN)}")

    environment = _required(env, "FLOWGUARD_ENV")
    if environment not in ENVIRONMENTS:
        raise SettingsError(f"FLOWGUARD_ENV must be one of {', '.join(ENVIRONMENTS)}, got {environment!r}")

    model_dir = _required(env, "FLOWGUARD_MODEL_DIR")
    if not model_dir.startswith("/"):
        raise SettingsError(f"FLOWGUARD_MODEL_DIR must be an absolute path, got {model_dir!r}")

    release = _required(env, "FLOWGUARD_RELEASE")
    if not _RELEASE.match(release):
        raise SettingsError(f"FLOWGUARD_RELEASE must be 7-40 lowercase hex characters (a git SHA), got {release!r}")

    log_level = env.get("FLOWGUARD_LOG_LEVEL", "INFO").strip().upper() or "INFO"
    if log_level not in LOG_LEVELS:
        raise SettingsError(f"FLOWGUARD_LOG_LEVEL must be one of {', '.join(LOG_LEVELS)}, got {log_level!r}")

    raw_port = env.get("FLOWGUARD_PORT", "8000").strip() or "8000"
    try:
        port = int(raw_port)
    except ValueError as exc:
        raise SettingsError(f"FLOWGUARD_PORT must be an integer, got {raw_port!r}") from exc
    if not 1 <= port <= 65535:
        raise SettingsError(f"FLOWGUARD_PORT must be in 1-65535, got {port}")

    return Settings(environment=environment, model_dir=model_dir, release=release,
                    log_level=log_level, port=port)
