"""Measure a build context described by a listing, after applying a .dockerignore (given tool).

    python labs/w6d1_docker_basics/challenge/context_report.py \
        labs/w6d1_docker_basics/challenge/broken/c_context/context_listing.tsv \
        labs/w6d1_docker_basics/challenge/fixed/c_context/.dockerignore

Prints what would be sent to the builder, by top-level directory, and the 15 largest files kept.
Uses the same matching rules as Docker (w6d1_dockerlint.DockerIgnore, a port of moby/patternmatcher).
With no .dockerignore argument (or a missing file) it shows the context as it is now.
"""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from w6d1_dockerlint import DockerIgnore  # noqa: E402


def read_listing(path: str | Path) -> list[tuple[str, int]]:
    rows = []
    for line in Path(path).read_text().splitlines():
        if line.strip():
            name, size = line.split("\t")
            rows.append((name, int(size)))
    return rows


def kept(rows, ignore: DockerIgnore) -> list[tuple[str, int]]:
    return [(p, s) for p, s in rows if not ignore.excluded(p)]


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    rows = read_listing(argv[0])
    ignore = DockerIgnore.from_file(argv[1]) if len(argv) > 1 else DockerIgnore("")
    keep = kept(rows, ignore)
    by_top = defaultdict(int)
    for path, size in keep:
        by_top[path.split("/")[0]] += size
    total = sum(s for _, s in rows)
    sent = sum(s for _, s in keep)
    print(f"context: {len(keep)} of {len(rows)} files, {sent / 1e6:,.2f} MB of {total / 1e6:,.1f} MB")
    for top, size in sorted(by_top.items(), key=lambda kv: -kv[1]):
        print(f"  {size / 1e6:>10,.2f} MB  {top}")
    print("largest files kept:")
    for path, size in sorted(keep, key=lambda kv: -kv[1])[:15]:
        print(f"  {size / 1e6:>10,.3f} MB  {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
