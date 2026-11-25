"""Worked example (w6d1): .dockerignore patterns are anchored at the context root.

    python labs/w6d1_docker_basics/example/dockerignore_demo.py            # offline prediction
    python labs/w6d1_docker_basics/example/dockerignore_demo.py --docker   # also verify with a real build

Creates a small project in a temporary directory with a .dockerignore written the way most people
write a .gitignore, then lists which files reach the build context. Offline, the decision comes
from w6d1_dockerlint.DockerIgnore (a port of Docker's own matcher, moby/patternmatcher). With
--docker it builds `FROM busybox` + `COPY . /ctx` and lists /ctx, so you can see Docker agree.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "checks"))
from w6d1_dockerlint import DockerIgnore, context_files  # noqa: E402

FILES = ["src/pkg/a.py", "src/pkg/__pycache__/a.cpython-312.pyc", "__pycache__/b.pyc", "a.pyc", "src/b.pyc",
         "data/raw/x.csv", "runs/r.bin", "exp/2026/runs/m.bin", "notebooks/.ipynb_checkpoints/n.ipynb",
         "README.md", "docs.md", "src/notes.md"]
DOCKERIGNORE = "__pycache__\n*.pyc\nruns\n**/.ipynb_checkpoints\n*.md\n!README.md\ndata\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--docker", action="store_true", help="verify with a real docker build (needs a daemon)")
    args = ap.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for rel in FILES:
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            (root / rel).write_text("x\n")
        (root / ".dockerignore").write_text(DOCKERIGNORE)
        (root / "Dockerfile").write_text('FROM busybox:1.36\nCOPY . /ctx\nCMD ["true"]\n')
        ignore = DockerIgnore(DOCKERIGNORE)
        print(".dockerignore:\n  " + DOCKERIGNORE.strip().replace("\n", "\n  "))
        print("\nfile                                   in context?")
        for rel in sorted(FILES):
            print(f"  {rel:<38} {'EXCLUDED' if ignore.excluded(rel) else 'sent'}")
        predicted = sorted(f for f in context_files(root) if not ignore.excluded(f))
        if args.docker:
            tag = f"dockerignore-demo:{uuid.uuid4().hex[:8]}"
            try:
                subprocess.run(["docker", "build", "-q", "-t", tag, str(root)], check=True, capture_output=True)
                out = subprocess.run(["docker", "run", "--rm", tag, "find", "/ctx", "-type", "f"],
                                     check=True, capture_output=True, text=True).stdout
                actual = sorted(line.removeprefix("/ctx/") for line in out.split())
            finally:
                subprocess.run(["docker", "image", "rm", "-f", tag], capture_output=True)
            print(f"\nreal docker build agrees with the prediction: {actual == predicted}")
            if actual != predicted:
                print("  differences:", sorted(set(actual) ^ set(predicted)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
