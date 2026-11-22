"""Why an untrusted pickle is untrusted code. A harmless, self-contained demonstration.

    python lessons/w5d2_artifacts_versioning/example/pickle_is_code.py

The "payload" below only prints a line and creates an empty marker file in a fresh temporary
directory, which is deleted at the end. Nothing else is executed. The same mechanism would run any
callable with any arguments: that is the point.
"""
from __future__ import annotations

import io
import pickle
import pickletools
import tempfile
from pathlib import Path

import numpy as np


class InnocentLookingModel:
    """What an attacker (or a careless colleague) could put in a file named model.pkl."""

    def __init__(self, marker: Path):
        self.marker = marker

    def __reduce__(self):
        # pickle stores "call open(marker, 'w') to rebuild me"; loading performs that call
        return (open, (str(self.marker), "w"))


class Announcer:
    def __reduce__(self):
        return (print, ("   >>> this line was printed by pickle.loads, not by the script <<<",))


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        marker = Path(tmp) / "created-by-unpickling.txt"
        blob = pickle.dumps([Announcer(), InnocentLookingModel(marker)], protocol=5)
        print(f"payload: {len(blob)} bytes. Disassembly (what pickle.loads will do):")
        out = io.StringIO()
        pickletools.dis(blob, out=out)
        for line in out.getvalue().splitlines():
            if any(k in line for k in ("STACK_GLOBAL", "REDUCE", "UNICODE")):
                print("   " + line.strip())
        print(f"marker exists before loading: {marker.exists()}")
        obj = pickle.loads(blob)
        obj[1].close()                                    # the "model" is an open file handle
        print(f"marker exists after loading:  {marker.exists()}")

        npz = Path(tmp) / "reference.npz"
        np.savez(npz, ok=np.arange(3.0), sneaky=np.array([{"a": 1}], dtype=object))
        with np.load(npz, allow_pickle=False) as data:
            print(f"numeric array with allow_pickle=False: {data['ok']}")
            try:
                data["sneaky"]
            except ValueError as exc:
                print(f"object array with allow_pickle=False: refused ({exc})")


if __name__ == "__main__":
    main()
