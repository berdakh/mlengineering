"""Clean-clone reproduction audit (reference solution, w8d1).

    python audit/clean_clone_check.py <repo path or URL> [--ref REF] [--log audit/REPRODUCTION_LOG.md]
                                      [--keep] [--work-dir DIR]

What it does, in order:

1. ``git clone`` the repository into a fresh temporary directory and check out ``--ref``. Only committed
   files exist there: anything your pipeline silently relied on (a local data file, a cache, a notebook
   output) is absent, which is the point.
2. Read ``REPRODUCE.toml`` from the clone (format below).
3. Static scans of tracked files: absolute paths to a home directory, and a requirements file in which
   every requirement is pinned with ``==``.
4. Create an isolated virtual environment (no system site packages) and install the requirements.
5. Run each declared step with the venv first on PATH, recording exit code, duration and the tail of the
   output. A ``ModuleNotFoundError`` becomes the finding ``missing_dependency``, a missing file becomes
   ``missing_file``.
6. Compare each headline number produced by the steps with the committed expected value, within its
   tolerance. Optionally run the steps twice and require identical headline numbers.
7. Write a Markdown log and a JSON record next to it. Exit 0 if the verdict is PASS, 1 if FAIL, 2 on
   usage errors.

REPRODUCE.toml
--------------
    [environment]
    requirements = "requirements.lock"      # every line pinned with ==
    [[step]]
    name = "evaluate"
    run = ["python", "-m", "toyproj", "evaluate"]
    timeout_s = 600
    [headline]
    produced = "results/headline.json"      # written by the steps
    expected = "expected/headline.json"     # committed
    repeat = 1                              # 2 = run the steps twice and require identical numbers
    [[headline.value]]
    key = "test.pr_auc"                     # dotted path; integers index lists
    abs_tol = 1e-9
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib
import venv
from pathlib import Path

ABS_PATH = re.compile(r"(?<![\w.])(/home/[A-Za-z0-9_.-]+|/Users/[A-Za-z0-9_.-]+|[A-Za-z]:\\\\Users\\\\)")
TEXT_SUFFIXES = {".py", ".toml", ".cfg", ".ini", ".txt", ".lock", ".json", ".yaml", ".yml", ".md",
                 ".sh", ".mk", ""}
PIN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*(\[[A-Za-z0-9,._-]+\])?(==|>=)[A-Za-z0-9.+!*-]+(\s*;.*)?(\s+--hash=\S+)*$")


# ----------------------------------------------------------------------------------------------- utils
def finding(code: str, detail: str) -> dict:
    return {"code": code, "detail": detail}


def git(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


def get_path(data, key: str):
    """Follow a dotted path ('test.0.pr_auc'); integers index lists. Raises KeyError if absent."""
    cur = data
    for part in key.split("."):
        if isinstance(cur, list):
            try:
                cur = cur[int(part)]
            except (ValueError, IndexError) as exc:
                raise KeyError(key) from exc
        elif isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            raise KeyError(key)
    return cur


# ------------------------------------------------------------------------------------------- the steps
def clone(source: str, ref: str, dest: Path) -> list[dict]:
    """Clone with git (never copy the working tree: untracked files must not leak into the audit)."""
    proc = git("clone", "--quiet", source, str(dest))
    if proc.returncode != 0:
        return [finding("clone_failed", proc.stderr.strip()[-500:])]
    if ref != "HEAD":
        proc = git("checkout", "--quiet", ref, cwd=dest)
        if proc.returncode != 0:
            return [finding("clone_failed", f"cannot check out {ref}: {proc.stderr.strip()[-300:]}")]
    return []


def tracked_files(repo: Path) -> list[Path]:
    out = git("ls-files", cwd=repo).stdout.split("\n")
    return [repo / f for f in out if f]


def scan_absolute_paths(repo: Path) -> list[dict]:
    found = []
    for path in tracked_files(repo):
        if path.suffix not in TEXT_SUFFIXES or not path.is_file() or path.stat().st_size > 2_000_000:
            continue
        try:
            text = path.read_text()
        except UnicodeDecodeError:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            match = ABS_PATH.search(line)
            if match:
                found.append(finding("absolute_path",
                                     f"{path.relative_to(repo)}:{lineno} refers to {match.group(1)!r}, "
                                     "which exists only on the author's machine"))
    return found


def read_requirements(repo: Path, name: str) -> tuple[list[str], list[dict]]:
    path = repo / name
    if not path.is_file():
        return [], [finding("missing_requirements_file", f"{name} is not committed")]
    reqs, problems = [], []
    for lineno, raw in enumerate(path.read_text().splitlines(), 1):
        line = raw.split(" #")[0].strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("-"):
            problems.append(finding("unpinned_requirement", f"{name}:{lineno} option {line!r} is not allowed"))
        elif not PIN.match(line):
            problems.append(finding("unpinned_requirement",
                                    f"{name}:{lineno} {line!r} is not pinned with == (a later install can differ)"))
        else:
            reqs.append(line)
    return reqs, problems


def make_venv(where: Path, requirements_file: Path | None, has_requirements: bool) -> tuple[Path, list[dict]]:
    """An isolated venv: system site packages are OFF, otherwise missing dependencies go unnoticed."""
    venv.EnvBuilder(system_site_packages=False, with_pip=has_requirements, clear=True).create(where)
    bindir = where / ("Scripts" if os.name == "nt" else "bin")
    python = bindir / ("python.exe" if os.name == "nt" else "python")
    if has_requirements and requirements_file is not None:
        proc = subprocess.run([str(python), "-m", "pip", "install", "--quiet", "--disable-pip-version-check",
                               "-r", str(requirements_file)], capture_output=True, text=True)
        if proc.returncode != 0:
            return bindir, [finding("install_failed", (proc.stdout + proc.stderr).strip()[-800:])]
    return bindir, []


def step_env(bindir: Path) -> dict:
    env = {k: v for k, v in os.environ.items()
           if k not in ("PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV", "WB_TARGET_DIR", "PYTHONSTARTUP")}
    env["PATH"] = str(bindir) + os.pathsep + env.get("PATH", "")
    env["VIRTUAL_ENV"] = str(bindir.parent)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def classify_failure(output: str) -> dict:
    mod = re.search(r"ModuleNotFoundError: No module named '([^']+)'", output)
    if mod:
        return finding("missing_dependency",
                       f"module {mod.group(1)!r} is imported but not installed by the declared requirements")
    missing = re.search(r"(FileNotFoundError|No such file or directory)[^\n]*", output)
    if missing:
        return finding("missing_file", f"a file the pipeline needs is not in the repository: {missing.group(0)[:300]}")
    return finding("step_failed", output.strip()[-500:])


def run_steps(repo: Path, steps: list[dict], bindir: Path) -> tuple[list[dict], list[dict]]:
    records, problems = [], []
    env = step_env(bindir)
    for step in steps:
        start = time.perf_counter()
        try:
            proc = subprocess.run(step["run"], cwd=repo, env=env, capture_output=True, text=True,
                                  timeout=float(step.get("timeout_s", 1800)))
            code, output = proc.returncode, proc.stdout + proc.stderr
        except subprocess.TimeoutExpired:
            code, output = -1, f"timed out after {step.get('timeout_s')} s"
        except FileNotFoundError as exc:
            code, output = -1, f"command not found: {exc}"
        seconds = time.perf_counter() - start
        records.append({"name": step["name"], "command": " ".join(step["run"]), "exit_code": code,
                        "seconds": round(seconds, 2), "output_tail": output.strip()[-400:]})
        if code != 0:
            problem = classify_failure(output) if code > 0 else finding("step_failed", output)
            problem["detail"] = f"step {step['name']!r}: " + problem["detail"]
            problems.append(problem)
            break
    return records, problems


def compare_headline(produced: dict, expected: dict, values: list[dict]) -> tuple[list[dict], list[dict]]:
    rows, problems = [], []
    for spec in values:
        key, tol = spec["key"], float(spec.get("abs_tol", 0.0))
        row = {"key": key, "abs_tol": tol}
        try:
            exp = get_path(expected, key)
        except KeyError:
            problems.append(finding("headline_missing", f"{key} is not in the committed expected file"))
            rows.append({**row, "expected": None, "produced": None, "abs_diff": None, "ok": False})
            continue
        try:
            got = get_path(produced, key)
        except KeyError:
            problems.append(finding("headline_missing", f"{key} was not produced by the steps"))
            rows.append({**row, "expected": exp, "produced": None, "abs_diff": None, "ok": False})
            continue
        if isinstance(exp, (int, float)) and isinstance(got, (int, float)) and not isinstance(exp, bool):
            diff = abs(float(got) - float(exp))
            ok = math.isfinite(diff) and diff <= tol
        else:
            diff, ok = None, got == exp
        rows.append({**row, "expected": exp, "produced": got, "abs_diff": diff, "ok": ok})
        if not ok:
            problems.append(finding("headline_mismatch",
                                    f"{key}: committed {exp!r}, reproduced {got!r} (tolerance {tol:g}); "
                                    "either the committed number was not produced by this code or the run is not reproducible"))
    return rows, problems


# ------------------------------------------------------------------------------------------- reporting
def cell(value) -> str:
    """A value safe inside a Markdown table cell."""
    return str(value).replace("|", "\\|").replace("\n", " ")


def write_log(record: dict, log_path: Path) -> None:
    lines = [f"# Reproduction log: {record['verdict']}", "",
             "Generated by `audit/clean_clone_check.py`. Do not edit by hand.", "",
             "| Field | Value |", "|---|---|",
             f"| Source | `{record['source']}` |",
             f"| Commit | `{record.get('commit') or 'unknown'}` |",
             f"| Audited at (UTC) | {record['started_utc']} |",
             f"| Auditor Python | {record['python']} on {record['platform']} |",
             f"| Total time | {record['total_seconds']:.1f} s |", "",
             "## Steps", "", "| Step | Command | Exit | Seconds |", "|---|---|---|---|"]
    for s in record["steps"]:
        lines.append(f"| {cell(s['name'])} | `{cell(s['command'])}` | {s['exit_code']} | {s['seconds']} |")
    if not record["steps"]:
        lines.append("| (none run) | | | |")
    lines += ["", "## Headline numbers", "", "| Key | Committed | Reproduced | Abs. difference | Tolerance | OK |",
              "|---|---|---|---|---|---|"]
    for h in record["headline"]:
        diff = "" if h["abs_diff"] is None else f"{h['abs_diff']:.3g}"
        lines.append(f"| `{h['key']}` | {cell(h['expected'])} | {cell(h['produced'])} | {diff} | {h['abs_tol']:g} | "
                     f"{'yes' if h['ok'] else '**no**'} |")
    if not record["headline"]:
        lines.append("| (not compared) | | | | | |")
    lines += ["", "## Findings", ""]
    lines += [f"* `{f['code']}`: {cell(f['detail'])}" for f in record["findings"]] or ["None."]
    lines += ["", f"**Verdict: {record['verdict']}**", ""]
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("\n".join(lines))
    log_path.with_suffix(".json").write_text(json.dumps(record, indent=2, sort_keys=True, default=str) + "\n")


# ------------------------------------------------------------------------------------------------ main
def audit(source: str, ref: str, work: Path) -> dict:
    started = time.perf_counter()
    record = {"source": source, "ref": ref, "commit": None, "python": platform.python_version(),
              "platform": platform.system(), "started_utc": dt.datetime.now(dt.UTC).strftime("%Y-%m-%d %H:%M"),
              "steps": [], "headline": [], "findings": []}
    repo = work / "clone"
    record["findings"] += clone(source, ref, repo)
    if not record["findings"]:
        record["commit"] = git("rev-parse", "HEAD", cwd=repo).stdout.strip()
        spec_path = repo / "REPRODUCE.toml"
        if not spec_path.is_file():
            record["findings"].append(finding("missing_spec", "REPRODUCE.toml is not committed"))
        else:
            spec = tomllib.loads(spec_path.read_text())
            record["findings"] += scan_absolute_paths(repo)
            req_name = spec.get("environment", {}).get("requirements", "requirements.lock")
            reqs, problems = read_requirements(repo, req_name)
            record["findings"] += problems
            if not problems:
                bindir, problems = make_venv(work / "venv", repo / req_name, bool(reqs))
                record["findings"] += problems
                if not problems:
                    head = spec.get("headline", {})
                    runs = []
                    for attempt in range(int(head.get("repeat", 1))):
                        if attempt:  # a repeat starts from the committed state again
                            git("clean", "-fdxq", "-e", "data/raw", cwd=repo)
                        steps, problems = run_steps(repo, spec.get("step", []), bindir)
                        record["steps"] += steps
                        record["findings"] += problems
                        if problems:
                            break
                        produced = repo / head.get("produced", "")
                        if not produced.is_file():
                            record["findings"].append(finding("headline_missing",
                                                              f"the steps did not write {head.get('produced')}"))
                            break
                        runs.append(json.loads(produced.read_text()))
                    if runs and not record["findings"]:
                        expected_path = repo / head.get("expected", "")
                        if not expected_path.is_file():
                            record["findings"].append(finding("headline_missing",
                                                              f"{head.get('expected')} is not committed"))
                        else:
                            rows, problems = compare_headline(runs[0], json.loads(expected_path.read_text()),
                                                              head.get("value", []))
                            record["headline"], record["findings"] = rows, record["findings"] + problems
                            for later in runs[1:]:
                                for spec_v in head.get("value", []):
                                    try:
                                        a, b = get_path(runs[0], spec_v["key"]), get_path(later, spec_v["key"])
                                    except KeyError:
                                        continue
                                    if a != b:
                                        record["findings"].append(finding(
                                            "nondeterministic", f"{spec_v['key']}: {a!r} on run 1, {b!r} on a repeat "
                                            "of the same commit; fix seeds, thread counts or ordering"))
    record["total_seconds"] = round(time.perf_counter() - started, 2)
    record["verdict"] = "PASS" if not record["findings"] else "FAIL"
    return record


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Reproduce a repository's headline numbers from a clean clone.")
    ap.add_argument("source", help="repository path or URL (anything `git clone` accepts)")
    ap.add_argument("--ref", default="HEAD", help="commit, tag or branch to audit")
    ap.add_argument("--log", default="audit/REPRODUCTION_LOG.md", help="Markdown log; a .json record goes next to it")
    ap.add_argument("--work-dir", help="use this empty directory instead of a temporary one")
    ap.add_argument("--keep", action="store_true", help="keep the clone and venv for inspection")
    args = ap.parse_args(argv)
    if args.work_dir:
        work = Path(args.work_dir)
        if work.exists() and any(work.iterdir()):
            print(f"error: --work-dir {work} is not empty", file=sys.stderr)
            return 2
        work.mkdir(parents=True, exist_ok=True)
    else:
        work = Path(tempfile.mkdtemp(prefix="clean-clone-"))
    try:
        record = audit(args.source, args.ref, work)
    finally:
        if not args.keep:
            shutil.rmtree(work, ignore_errors=True)
    write_log(record, Path(args.log))
    print(f"{record['verdict']}: {len(record['findings'])} finding(s); log written to {args.log}")
    for f in record["findings"]:
        print(f"  {f['code']}: {f['detail']}")
    return 0 if record["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
