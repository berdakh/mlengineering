"""Worked example (w6d5): a minimal secret scanner, and why it belongs before `git commit`.

    python lessons/w6d5_cloud_deployment/example/secret_scan.py --demo     # scans a SYNTHETIC tree
    python lessons/w6d5_cloud_deployment/example/secret_scan.py PATH ...   # scans your own files

The demo builds a throw-away project in a temporary directory with the mistakes people actually
make: a key pasted into a notebook, a credentials file next to the code, an account id in a config.
Every "credential" is fake and assembled at run time, so this file itself contains none.

Real tools (gitleaks, trufflehog, GitHub secret scanning, detect-secrets) use hundreds of patterns plus
entropy checks and verify candidates against the provider. This one has four rules, enough to show the
mechanism and its two failure modes: false positives (a 12-digit order number) and false negatives (a
key split across two strings, as in this file).
"""
from __future__ import annotations

import argparse
import re
import sys
import tempfile
from pathlib import Path

RULES = [
    ("aws-access-key-id", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("aws-secret-key-assignment", re.compile(r"(?i)aws_secret_access_key\s*[=:]\s*['\"]?[A-Za-z0-9/+]{40}")),
    ("aws-account-id", re.compile(r"(?<![\d.])\d{12}(?![\d.])")),
    ("private-key-block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
]
SKIP_SUFFIXES = {".png", ".svg", ".whl", ".pyc", ".npz", ".db"}


def scan(paths: list[Path]) -> list[tuple[str, int, str]]:
    hits = []
    for root in paths:
        files = [root] if root.is_file() else sorted(p for p in root.rglob("*") if p.is_file())
        for f in files:
            if f.suffix in SKIP_SUFFIXES or ".git" in f.parts:
                continue
            for lineno, line in enumerate(f.read_text(errors="ignore").splitlines(), 1):
                for rule, pattern in RULES:
                    if pattern.search(line):
                        hits.append((str(f), lineno, rule))
    return hits


def demo_tree(tmp: Path) -> Path:
    fake_id = "AKIA" + "Q" * 4 + "EXAMPLE" + "FAKEF"           # 20 chars, assembled: never a real key
    fake_secret = "wJalrXUtnFEMI" + "K7MDENG" + "bPxRfiCYEXAMPLEKEY12"  # 40 chars, AWS's documented style
    proj = tmp / "demo-project"
    (proj / "notebooks").mkdir(parents=True)
    (proj / "config").mkdir()
    (proj / "notebooks" / "explore.py").write_text(f'import boto3\nkey_id = "{fake_id}"  # TODO remove\n')
    (proj / "config" / "aws_credentials").write_text(
        f"[default]\naws_access_key_id = {fake_id}\naws_secret_access_key = {fake_secret}\n")
    (proj / "config" / "deploy.toml").write_text('[aws]\naccount_id = "' + "1234" * 3 + '"\nregion = "eu-west-1"\n')
    (proj / "orders.csv").write_text("order_id,qty\n" + "9876" * 3 + ",3\n")            # a false positive
    split = '"AKIA" + "' + "Z" * 16 + '"'
    (proj / "sneaky.py").write_text(f"key = {split}  # split across two strings\n")    # a false negative
    return proj


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("paths", nargs="*", type=Path)
    ap.add_argument("--demo", action="store_true")
    args = ap.parse_args(argv)
    with tempfile.TemporaryDirectory() as tmp:
        paths = [demo_tree(Path(tmp))] if args.demo else args.paths
        if not paths:
            ap.error("give paths or --demo")
        hits = scan(paths)
        base = str(paths[0]) if args.demo else ""
        for f, lineno, rule in hits:
            print(f"{f.replace(base, '<demo>')}:{lineno}: {rule}")
    print(f"{len(hits)} finding(s)")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
