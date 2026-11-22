"""Roll an environment back to the previous known-good image, pinned by digest. REFERENCE SOLUTION (w6d6).

    python ops/rollback.py production            # show what would be deployed, and the docker command
    python ops/rollback.py production --apply    # do it, and mark the current deployment rolled_back

Contract (graded by the checks)
-------------------------------
A history entry is a dict with ``env``, ``release``, ``image``, ``digest`` (``sha256:...``),
``deployed_at`` (ISO 8601, sortable) and ``status`` (``good`` / ``failed`` / ``rolled_back``).

``select_rollback_target(history, env) -> dict``
    The environment's *current* deployment is its entry with the latest ``deployed_at`` (the list is
    not guaranteed to be in order). The target is the most recent earlier entry of the same
    environment whose status is ``good`` and whose digest differs from the current digest: rolling
    back to the image that is already running changes nothing. Raises ``RollbackError`` when the
    environment has no deployments or no such earlier entry exists.
``image_reference(entry) -> str``
    ``"<image>@<digest>"``. Never a tag: tags can be moved, digests cannot.

What a rollback does NOT fix: a configuration change (env file, memory limit) made with the same
image. Then the "previous good digest" is the image that is already running; the fix is to revert the
configuration and redeploy the same digest. The lesson's incidents include both kinds.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


class RollbackError(RuntimeError):
    """No sensible rollback target exists."""


def select_rollback_target(history: list[dict], env: str) -> dict:
    entries = sorted((e for e in history if e.get("env") == env), key=lambda e: e["deployed_at"])
    if not entries:
        raise RollbackError(f"{env} has no deployments")
    current = entries[-1]
    for entry in reversed(entries[:-1]):
        if entry.get("status") == "good" and entry["digest"] != current["digest"]:
            return entry
    raise RollbackError(f"{env}: no earlier good deployment with a different image than the current "
                        f"{current['digest'][:19]}...; if the image is fine, fix the configuration instead")


def image_reference(entry: dict) -> str:
    return f"{entry['image']}:{entry['release']}"


def main(argv: list[str] | None = None) -> int:
    import fgops  # given; imported here so the functions above stay importable without Docker

    ap = argparse.ArgumentParser(description="Roll an environment back to its previous good image.")
    ap.add_argument("env", choices=fgops.ENVIRONMENTS)
    ap.add_argument("--apply", action="store_true", help="deploy it (default: only show the plan)")
    args = ap.parse_args(argv)
    history = fgops.load_history()
    try:
        target = select_rollback_target(history, args.env)
        ref = image_reference(target)
    except RollbackError as exc:
        print(f"no rollback: {exc}", file=sys.stderr)
        return 1
    print(f"rollback target for {args.env}: release {target['release']} deployed {target['deployed_at']}")
    print("docker " + " ".join(fgops.run_args(args.env, target["release"], target["digest"])))
    if not args.apply:
        print("(plan only; add --apply to deploy it)")
        return 0
    current = max((e for e in history if e["env"] == args.env), key=lambda e: e["deployed_at"])
    current["status"] = "rolled_back"
    fgops.save_history(history)
    entry = fgops.deploy(args.env, ref, note=f"rollback from {current['release']}")
    return 0 if entry["status"] == "good" else 2


if __name__ == "__main__":
    sys.exit(main())
