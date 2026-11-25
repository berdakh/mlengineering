"""Rebuild the worked example's Git history in a scratch directory so you can inspect it.

    python labs/w1d6_notebook_to_package/example/replay_history.py /tmp/meters-demo
    cd /tmp/meters-demo && git log --oneline && git show --stat HEAD~1

Each directory in steps/ holds the files ADDED OR CHANGED by one commit (not a full
snapshot) plus COMMIT_MESSAGE.txt. After every commit the test suite is run, because
"every commit passes its tests" is the property the example demonstrates.
Commit hashes will differ from the ones printed in the lesson (they depend on time).
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

STEPS = Path(__file__).resolve().parent / "steps"
GIT = ["git", "-c", "user.name=Course Example", "-c", "user.email=example@example.invalid"]


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    repo = Path(sys.argv[1]).resolve()
    if repo.exists() and any(repo.iterdir()):
        print(f"refusing to write into non-empty directory {repo}", file=sys.stderr)
        return 2
    repo.mkdir(parents=True, exist_ok=True)
    run(["git", "init", "-q", "-b", "main"], repo)
    for step in sorted(p for p in STEPS.iterdir() if p.is_dir()):
        message = (step / "COMMIT_MESSAGE.txt").read_text().strip()
        # copyfile (not the default copy2) so files get a fresh modification time: Git decides whether a
        # file changed from its size and mtime first, and two versions of golden.txt have the same size.
        shutil.copytree(step, repo, dirs_exist_ok=True, copy_function=shutil.copyfile,
                        ignore=shutil.ignore_patterns("COMMIT_MESSAGE.txt"))
        run([*GIT, "add", "-A"], repo)
        run([*GIT, "commit", "-q", "-m", message], repo)
        tests = run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"], repo)
        summary = tests.stdout.strip().splitlines()[-1] if tests.stdout.strip() else "no output"
        print(f"{step.name:<26} tests: {summary}")
    print()
    print(run(["git", "log", "--oneline"], repo).stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
