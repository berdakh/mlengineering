"""Generate broken/c_context/context_listing.tsv: a SYNTHETIC but realistic project directory.

    python labs/w6d1_docker_basics/challenge/make_listing.py

One line per file: <path relative to the build context> TAB <size in bytes>. The sizes are made
up (seeded), the structure is typical of an ML project after a few weeks of work. Nothing of this
size is in the repository: a listing lets you measure a .dockerignore without 1 GB on disk.
"""
from __future__ import annotations

import random
from pathlib import Path

OUT = Path(__file__).resolve().parent / "broken" / "c_context" / "context_listing.tsv"
MB = 1_000_000


def build() -> list[tuple[str, int]]:
    rng = random.Random(20261122)
    files: list[tuple[str, int]] = []
    add = lambda path, size: files.append((path, int(size)))  # noqa: E731
    # what the image needs
    for name in ("__init__", "api", "bundle", "data", "inference", "schemas", "splits", "evaluation", "operating"):
        add(f"src/flowguard/{name}.py", rng.randint(1_500, 9_000))
        add(f"src/flowguard/__pycache__/{name}.cpython-312.pyc", rng.randint(2_000, 12_000))
    add("models/flowguard-z/1.0.0/model.json", 1_026)
    add("models/flowguard-z/1.0.0/checksums.json", 87)
    add("requirements.txt", 265)
    add("pyproject.toml", 496)
    add("README.md", 6_210)
    add("Dockerfile", 980)
    # development material
    add("requirements-dev.txt", 237)
    for name in ("build_bundle", "make_request", "make_smoke_fixture"):
        add(f"scripts/{name}.py", rng.randint(2_000, 4_000))
        add(f"scripts/__pycache__/{name}.cpython-312.pyc", rng.randint(2_000, 5_000))
    for name in ("test_api", "test_bundle", "test_inference", "conftest"):
        add(f"tests/{name}.py", rng.randint(1_000, 6_000))
        add(f"tests/__pycache__/{name}.cpython-312-pytest-9.1.1.pyc", rng.randint(3_000, 9_000))
    add(".pytest_cache/v/cache/nodeids", 4_100)
    add(".pytest_cache/v/cache/lastfailed", 120)
    for i in range(6):
        add(f"notebooks/0{i}_exploration.ipynb", rng.randint(200_000, 1_500_000))
        add(f"notebooks/.ipynb_checkpoints/0{i}_exploration-checkpoint.ipynb", rng.randint(200_000, 1_500_000))
    add(".env", 212)                                     # local credentials: must never reach an image
    # version control
    add(".git/HEAD", 23)
    add(".git/config", 312)
    add(".git/index", 48_000)
    for i in range(3):
        add(f".git/objects/pack/pack-{i:02d}.pack", rng.randint(40 * MB, 60 * MB))
    # a local virtual environment
    for pkg, total in (("numpy", 67), ("pandas", 74), ("scipy", 110), ("matplotlib", 38), ("torch", 95), ("jupyterlab", 21)):
        n = rng.randint(30, 60)
        for k in range(n):
            add(f".venv/lib/python3.12/site-packages/{pkg}/part_{k:03d}.so", total * MB / n)
    # data
    for family, count in (("valve1", 16), ("valve2", 4), ("other", 14)):
        for k in range(count):
            add(f"data/raw/skab/{family}/{k}.csv", rng.randint(70_000, 130_000))
    for k in range(12):
        add(f"data/processed/features_v{k}.csv", rng.randint(15 * MB, 30 * MB))
    # run outputs at the root and nested inside experiment folders
    for k in range(8):
        add(f"runs/2026110{k}-0930/model.npz", rng.randint(2 * MB, 6 * MB))
        add(f"runs/2026110{k}-0930/metrics.json", 900)
    for month in ("2026-10", "2026-11"):
        for k in range(5):
            add(f"experiments/{month}/sweep_{k}/runs/r{k}/checkpoint.pt", rng.randint(15 * MB, 25 * MB))
            add(f"experiments/{month}/sweep_{k}/config.toml", 640)
    return files


def main() -> None:
    files = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("".join(f"{p}\t{s}\n" for p, s in files))
    print(f"wrote {OUT}: {len(files)} files, {sum(s for _, s in files) / 1e9:.2f} GB")


if __name__ == "__main__":
    main()
