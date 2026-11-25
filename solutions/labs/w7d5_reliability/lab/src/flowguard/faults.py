"""Fault injection for drills and tests. GIVEN in the lab; you do not need to edit it.

Faults are switched on by the environment variable FLOWGUARD_FAULTS (read once, when the app is
created) or by passing ``faults=`` to ``create_app``. Format: comma-separated names, some with a value:

    FLOWGUARD_FAULTS="model_error"            scoring raises RuntimeError
    FLOWGUARD_FAULTS="nan_scores"             scoring returns NaN for every value (a silent wrong answer)
    FLOWGUARD_FAULTS="slow_model=0.5"         scoring sleeps 0.5 s first (a slow dependency)
    FLOWGUARD_FAULTS="bundle_corrupt"         the model bundle is treated as unloadable at startup

Never enable faults in production configuration. The hooks exist so that every failure mode the
service claims to handle has a test that actually produces it.
"""
from __future__ import annotations

import os

FAULTS_ENV = "FLOWGUARD_FAULTS"
KNOWN_FAULTS = {"model_error": False, "nan_scores": False, "slow_model": True, "bundle_corrupt": False}


def parse_faults(spec: str | None) -> dict[str, float | None]:
    """'model_error,slow_model=0.5' -> {'model_error': None, 'slow_model': 0.5}. Unknown names raise."""
    faults: dict[str, float | None] = {}
    for item in (spec or "").split(","):
        item = item.strip()
        if not item:
            continue
        name, _, value = item.partition("=")
        name = name.strip()
        if name not in KNOWN_FAULTS:
            raise ValueError(f"unknown fault {name!r}; known: {sorted(KNOWN_FAULTS)}")
        if KNOWN_FAULTS[name]:
            if not value:
                raise ValueError(f"fault {name!r} needs a value, e.g. {name}=0.5")
            faults[name] = float(value)
        else:
            if value:
                raise ValueError(f"fault {name!r} takes no value")
            faults[name] = None
    return faults


def faults_from_env() -> dict[str, float | None]:
    return parse_faults(os.environ.get(FAULTS_ENV))
