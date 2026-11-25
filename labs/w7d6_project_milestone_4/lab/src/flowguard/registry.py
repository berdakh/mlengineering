"""A local model registry: immutable versions, a CURRENT pointer, a promotion history. GIVEN.

    models/
      flowrate-z-2026.11/   MANIFEST.json, model.json    (never modified after registration)
      flowrate-z-2026.12/   ...
      CURRENT               one line: the serving version
      HISTORY.jsonl         one JSON object per promotion or rollback

The service is started with FLOWGUARD_MODEL_DIR=<registry>/<CURRENT>; changing CURRENT does nothing to a
running process. A promotion or rollback is complete only after the service has been restarted and
/version reports the new model_version.
"""
from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path

from flowguard.bundle import load_bundle


class RegistryError(Exception):
    pass


class Registry:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def versions(self) -> list[str]:
        return sorted(p.name for p in self.root.iterdir() if (p / "MANIFEST.json").is_file())

    def register(self, bundle_dir: str | Path) -> str:
        model = load_bundle(bundle_dir)                      # refuses invalid bundles
        target = self.root / model.model_version
        if target.exists():
            raise RegistryError(f"version {model.model_version} already registered (versions are immutable)")
        shutil.copytree(bundle_dir, target)
        return model.model_version

    def current(self) -> str | None:
        path = self.root / "CURRENT"
        return path.read_text().strip() if path.is_file() else None

    def path(self, version: str | None = None) -> Path:
        version = version or self.current()
        if version is None or not (self.root / version / "MANIFEST.json").is_file():
            raise RegistryError(f"unknown version {version!r}")
        return self.root / version

    def history(self) -> list[dict]:
        path = self.root / "HISTORY.jsonl"
        return [json.loads(line) for line in path.read_text().splitlines()] if path.is_file() else []

    def _set_current(self, version: str, action: str, reason: str) -> None:
        self.path(version)
        tmp = self.root / "CURRENT.tmp"
        tmp.write_text(version + "\n")
        os.replace(tmp, self.root / "CURRENT")              # atomic pointer switch
        with (self.root / "HISTORY.jsonl").open("a") as fh:
            fh.write(json.dumps({"ts": round(time.time(), 3), "action": action, "version": version,
                                 "reason": reason}) + "\n")

    def promote(self, version: str, reason: str = "") -> None:
        self._set_current(version, "promote", reason)

    def rollback(self, reason: str = "") -> str:
        """Point CURRENT at the version that was current before the latest one; returns it."""
        served = [h["version"] for h in self.history()]
        current = self.current()
        previous = [v for v in served if v != current]
        if not previous:
            raise RegistryError("no earlier version to roll back to")
        self._set_current(previous[-1], "rollback", reason)
        return previous[-1]
