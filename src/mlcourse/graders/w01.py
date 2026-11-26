"""Week 1 graders: Colab and the course (01), Python for engineers (02), terminal and Git (03), lab (04)."""
from __future__ import annotations

import csv
import json
import math
import subprocess
import tempfile
from pathlib import Path

from mlcourse.grader import exercise, register_quiz


# ----------------------------------------------------------------------------- helpers
def _git(repo: Path, *args: str) -> str:
    out = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if out.returncode != 0:
        raise AssertionError(f"`git {' '.join(args)}` failed in {repo}: {out.stderr.strip()[:200]}")
    return out.stdout


def _repo(answer) -> Path:
    path = Path(str(answer))
    assert path.is_dir(), f"{path} is not a folder. Did you run the cells that create it?"
    assert (path / ".git").is_dir(), f"{path} is not a Git repository yet (no .git folder). Run `git init` there."
    return path


def _commits(repo: Path, ref: str = "HEAD") -> list[str]:
    out = subprocess.run(["git", "-C", str(repo), "log", "--format=%H %s", ref], capture_output=True, text=True)
    return [line for line in out.stdout.splitlines() if line.strip()] if out.returncode == 0 else []


def _write(tmp: Path, name: str, text: str) -> Path:
    p = tmp / name
    p.write_text(text, encoding="utf-8")
    return p


# ============================================================================ 01 Welcome and Colab
@exercise("w01.add", hint="Use the + operator and return the result (do not print it).")
def _(fn):
    for a, b in [(2, 3), (-1, 1), (0.5, 0.25), (100, -250)]:
        got = fn(a, b)
        assert got is not None, "your function returns None: did you forget `return`?"
        assert math.isclose(got, a + b), f"add({a}, {b}) should be {a + b}, got {got}"


@exercise("w01.course_hours", hint="Add the minutes, divide by 60, then round(..., 1).")
def _(fn):
    cases = [([60, 60], 2.0), ([75, 100, 100, 90], 6.1), ([], 0.0), ([30], 0.5), ([45, 50], 1.6)]
    for minutes, want in cases:
        got = fn(minutes)
        assert got is not None, "your function returns None: did you forget `return`?"
        assert math.isclose(got, want), f"course_hours({minutes}) should be {want}, got {got}"


@exercise("w01.notebooks_in_week", hint="json.load the file, keep entries whose 'week' matches, return their 'title's in order.")
def _(fn):
    from mlcourse.paths import repo_root
    data = json.loads((repo_root() / "curriculum.json").read_text())
    for week in (1, 2, 12):
        want = [n["title"] for n in data["notebooks"] if n["week"] == week]
        got = fn(week)
        assert isinstance(got, list), f"notebooks_in_week({week}) should return a list, got {type(got).__name__}"
        assert got == want, f"notebooks_in_week({week}) returned {len(got)} titles; expected {len(want)}, in course order"
    assert fn(99) == [], "a week that does not exist should give an empty list"


@exercise("w01.count_course_databases", hint="List data/course with `!ls data/course` and count the files ending in .db.")
def _(n):
    from mlcourse.paths import repo_root
    want = len(list((repo_root() / "data" / "course").glob("*.db")))
    assert isinstance(n, int), f"put a whole number in n_databases, not {type(n).__name__}"
    assert n == want, f"{n} is not the number of .db files in data/course"


@exercise("w01.save_note", hint="Open the file with mode 'w', write the text, and return the Path.")
def _(fn):
    with tempfile.TemporaryDirectory() as tmp:
        for i, text in enumerate(["hello", "Line one\nLine two\n", ""]):
            target = Path(tmp) / f"sub{i}" / "note.txt"
            got = fn(text, target)
            assert target.is_file(), f"save_note did not create {target.name} (does it create missing folders?)"
            assert target.read_text(encoding="utf-8") == text, "the file content is not exactly the text you were given"
            assert Path(got) == target, "save_note should return the path it wrote"


@exercise("w01.load_or_default", hint="Check path.exists() (or catch FileNotFoundError) before reading.")
def _(fn):
    with tempfile.TemporaryDirectory() as tmp:
        p = _write(Path(tmp), "x.txt", "saved text")
        assert fn(p, "fallback") == "saved text", "when the file exists, return its content"
        assert fn(Path(tmp) / "missing.txt", "fallback") == "fallback", "when the file is missing, return the default"
        assert fn(Path(tmp) / "nope" / "deeper.txt", None) is None, "a missing folder is also 'missing'"


@exercise("w01.runtime_survivors", hint="Only the repository files cloned from GitHub come back after a reset; your edits and variables do not.")
def _(answer):
    assert isinstance(answer, (set, list, tuple)), "give a set of letters, e.g. {'a', 'c'}"
    got = {str(a).strip().lower() for a in answer}
    assert got == {"c"}, "not quite: which of these is stored somewhere other than the runtime's own disk and memory?"


@exercise("w01.minutes_to_text", hint="Use divmod(minutes, 60) and an f-string; leave out a part that is zero.")
def _(fn):
    cases = {75: "1 h 15 min", 120: "2 h", 45: "45 min", 0: "0 min", 61: "1 h 1 min"}
    for m, want in cases.items():
        got = fn(m)
        assert got == want, f"minutes_to_text({m}) should be {want!r}, got {got!r}"


register_quiz("w01.01_q1", "b",
              "A notebook remembers the order you ran cells in, not the order they appear in; restarting and "
              "running top to bottom is the only way to know the notebook really works.",
              {"a": "Cells do not re-run automatically when you edit something above them.",
               "c": "Colab keeps variables until the runtime restarts, whether or not you save.",
               "d": "Order matters a lot: a cell sees whatever earlier runs left in memory."})
register_quiz("w01.01_q2", "c",
              "The runtime is a temporary virtual machine; anything not saved to Drive or GitHub is deleted with it.",
              {"a": "Files you create in /content are deleted when the runtime is recycled.",
               "b": "Saving the notebook saves its text, not the files your code wrote.",
               "d": "Your browser only shows the notebook; the files live on the remote machine."})
register_quiz("w01.01_q3", "a",
              "The grader checks behaviour on several inputs; passing means your code works for those cases, "
              "not that it is perfect, and failing tells you what to look at.",
              {"b": "Graders never show the solution; they describe what went wrong.",
               "c": "You can re-run a grader as many times as you like.",
               "d": "Passing the grader is guided practice; the challenge-style tasks show independence."})
register_quiz("w01.01_q4", "d",
              "Prefixing a line with ! runs it in the machine's shell, which is how you use command-line tools from Colab.",
              {"a": "! is not a Python operator here; it hands the line to the shell.",
               "b": "Comments start with #, not !.",
               "c": "Installing is one use of the shell (!pip install), but ! runs any shell command."})


# ============================================================================ 02 Python for engineers
@exercise("w01.c_to_f", hint="F = C * 9/5 + 32. Return a float.")
def _(fn):
    for c, f in [(0, 32.0), (100, 212.0), (-40, -40.0), (36.6, 97.88)]:
        got = fn(c)
        assert got is not None and math.isclose(got, f, abs_tol=1e-9), f"c_to_f({c}) should be {f}, got {got}"


@exercise("w01.safe_divide", hint="Check for a zero denominator before dividing and return None in that case.")
def _(fn):
    assert math.isclose(fn(10, 4), 2.5), "safe_divide(10, 4) should be 2.5"
    assert math.isclose(fn(-9, 3), -3.0), "safe_divide(-9, 3) should be -3.0"
    assert fn(5, 0) is None, "dividing by zero should return None, not raise"
    assert fn(0, 0) is None, "0 / 0 should also return None"


@exercise("w01.parse_price", hint="Strip spaces, remove '$' and ',', then float(); wrap float() in try/except and raise ValueError.")
def _(fn):
    for text, want in [("$1,234.50", 1234.5), ("12", 12.0), (" $0.99 ", 0.99), ("1,000", 1000.0)]:
        got = fn(text)
        assert got is not None and math.isclose(got, want), f"parse_price({text!r}) should be {want}, got {got}"
    for bad in ["", "abc", "$", "12.3.4"]:
        try:
            fn(bad)
        except ValueError:
            continue
        except Exception as err:  # noqa: BLE001
            raise AssertionError(f"parse_price({bad!r}) raised {type(err).__name__}; it should raise ValueError") from None
        raise AssertionError(f"parse_price({bad!r}) should raise ValueError, but it returned a value")


@exercise("w01.word_counts", hint="Lower-case the text, split on whitespace, strip punctuation .,!? from each word, skip empty words.")
def _(fn):
    assert fn("") == {}, "empty text should give an empty dict"
    assert fn("a A a") == {"a": 3}, "counting should ignore upper/lower case"
    assert fn("Hello, world! Hello.") == {"hello": 2, "world": 1}, "punctuation .,!? at word ends should be removed"
    assert fn("one  two\tthree\none") == {"one": 2, "two": 1, "three": 1}, "split on any whitespace (spaces, tabs, newlines)"


@exercise("w01.top_n", hint="sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:n]")
def _(fn):
    counts = {"b": 3, "a": 3, "c": 5, "d": 1}
    assert fn(counts, 2) == [("c", 5), ("a", 3)], "highest counts first; ties broken alphabetically"
    assert fn(counts, 10) == [("c", 5), ("a", 3), ("b", 3), ("d", 1)], "n larger than the dict returns everything"
    assert fn({}, 3) == [], "an empty dict gives an empty list"
    assert fn(counts, 0) == [], "n = 0 gives an empty list"


@exercise("w01.squares_of_evens", hint="[x * x for x in numbers if x % 2 == 0]")
def _(fn):
    assert fn([1, 2, 3, 4]) == [4, 16]
    assert fn([]) == [], "an empty list gives an empty list"
    assert fn([-2, 0, 7]) == [4, 0], "negative even numbers and zero count as even"


@exercise("w01.invert", hint="Loop over items; use setdefault(value, []).append(key); sort each list at the end.")
def _(fn):
    assert fn({"a": 1, "b": 2, "c": 1}) == {1: ["a", "c"], 2: ["b"]}, "keys sharing a value go into one sorted list"
    assert fn({}) == {}, "an empty dict inverts to an empty dict"
    assert fn({"z": "x", "y": "x"}) == {"x": ["y", "z"]}, "each list must be sorted"


@exercise("w01.validate_age", hint="isinstance(value, int) and not isinstance(value, bool); raise TypeError or ValueError.")
def _(fn):
    for ok in (0, 18, 120):
        assert fn(ok) == ok, f"validate_age({ok}) should return {ok}"
    for bad, err in [("18", TypeError), (17.5, TypeError), (True, TypeError), (-1, ValueError), (121, ValueError)]:
        try:
            fn(bad)
        except err:
            continue
        except Exception as e:  # noqa: BLE001
            raise AssertionError(f"validate_age({bad!r}) raised {type(e).__name__}; expected {err.__name__}") from None
        raise AssertionError(f"validate_age({bad!r}) should raise {err.__name__}")


@exercise("w01.read_numbers", hint="Read the text, splitlines(), strip each line, skip empty ones, convert with float().")
def _(fn):
    with tempfile.TemporaryDirectory() as tmp:
        p = _write(Path(tmp), "n.txt", "1\n2.5\n\n  -3 \n")
        got = fn(p)
        assert got == [1.0, 2.5, -3.0], f"expected [1.0, 2.5, -3.0], got {got}"
        assert fn(_write(Path(tmp), "e.txt", "")) == [], "an empty file gives an empty list"
        assert fn(str(p)) == [1.0, 2.5, -3.0], "accept the path as a string too (wrap it in Path)"


@exercise("w01.json_round_trip", hint="json.dumps/json.dump to write, json.load to read back; return what you read.")
def _(fn):
    with tempfile.TemporaryDirectory() as tmp:
        for data in [{"a": 1, "b": [1, 2]}, [], {"nested": {"x": "y"}}]:
            target = Path(tmp) / "d.json"
            got = fn(data, target)
            assert target.is_file(), "the function must write the file"
            assert json.loads(target.read_text()) == data, "the file does not contain the data as JSON"
            assert got == data, "return the data you read back from the file"


@exercise("w01.column_mean", hint="csv.DictReader; skip rows where the value is empty; return None if nothing is left.")
def _(fn):
    with tempfile.TemporaryDirectory() as tmp:
        p = _write(Path(tmp), "t.csv", "name,score\nA,10\nB,\nC,20\nD,30\n")
        assert math.isclose(fn(p, "score"), 20.0), "mean of 10, 20, 30 should be 20.0 (skip the empty value)"
        q = _write(Path(tmp), "u.csv", "name,score\nA,\n")
        assert fn(q, "score") is None, "a column with no values should give None"


@exercise("w01.find_files", hint="Path(folder).rglob(f'*{suffix}'), keep files, return sorted names relative to folder (as strings).")
def _(fn):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "a").mkdir()
        for name in ["x.csv", "a/y.csv", "a/z.txt", "w.CSV.bak"]:
            (root / name).write_text("")
        got = fn(root, ".csv")
        assert got == ["a/y.csv", "x.csv"], f"expected ['a/y.csv', 'x.csv'], got {got}"
        assert fn(root, ".parquet") == [], "no matches gives an empty list"


register_quiz("w01.02_q1", "c",
              "Raising a specific exception stops bad data at the boundary with a clear message; returning a "
              "sentinel like -1 lets the bad value travel on silently.",
              {"a": "Printing does not stop the program; the caller continues with a bad value.",
               "b": "-1 looks like a real number to the next step, which is exactly the problem.",
               "d": "Catching every exception hides real bugs as well as bad input."})
register_quiz("w01.02_q2", "b",
              "Type hints document intent and let tools (and you) catch mistakes; Python does not enforce them at run time.",
              {"a": "Python ignores hints at run time: a str passed to an int-hinted function still runs.",
               "c": "Hints do not change speed.",
               "d": "They are used everywhere in modern codebases, especially in libraries and APIs."})
register_quiz("w01.02_q3", "a",
              "pathlib's / operator builds paths that work on Linux, macOS and Windows; string concatenation "
              "hard-codes one separator.",
              {"b": "Both can read files; the difference is building paths safely.",
               "c": "pathlib is part of the standard library.",
               "d": "Path objects are accepted by open(), pandas and almost every library."})
register_quiz("w01.02_q4", "d",
              "JSON keeps the structure (nested dicts and lists, numbers vs strings); CSV is a flat table of text.",
              {"a": "JSON files are usually larger than CSV for the same table.",
               "b": "Both are plain text that people can read.",
               "c": "CSV cannot represent nesting without inventing conventions."})
register_quiz("w01.02_q5", "b",
              "A docstring says what the function does, its inputs and outputs; it is what `help()` and editors show.",
              {"a": "Comments explain tricky lines; docstrings describe the function's contract.",
               "c": "Docstrings are never executed.",
               "d": "Every public function should have one; private helpers are optional."})


# ============================================================================ 03 Terminal and Git
@exercise("w01.line_count", hint="Run `!wc -l /tmp/shell-practice/server.log` and read the number.")
def _(n):
    p = Path("/tmp/shell-practice/server.log")
    assert p.is_file(), "the practice log does not exist: run the cell that creates /tmp/shell-practice first"
    want = len(p.read_text().splitlines())
    assert n == want, f"{n} is not the number of lines in server.log"


@exercise("w01.error_count", hint="grep -c ERROR counts the lines that contain ERROR.")
def _(n):
    p = Path("/tmp/shell-practice/server.log")
    want = sum("ERROR" in line for line in p.read_text().splitlines())
    assert n == want, f"{n} is not the number of lines that contain ERROR"


@exercise("w01.busiest_endpoint", hint="Extract the endpoint column with cut, then sort | uniq -c | sort -rn | head -1.")
def _(answer):
    p = Path("/tmp/shell-practice/server.log")
    from collections import Counter
    counts = Counter(line.split()[3] for line in p.read_text().splitlines() if len(line.split()) > 3)
    want = counts.most_common(1)[0][0]
    assert str(answer).strip() == want, f"{answer!r} is not the endpoint that appears most often"


@exercise("w01.shell_file", hint="Use > to create the file and >> to append the second line.")
def _(answer):
    p = Path(str(answer))
    assert p.is_file(), f"{p} does not exist"
    lines = p.read_text().splitlines()
    assert lines == ["first line", "second line"], f"expected the two lines 'first line' and 'second line', got {lines}"


@exercise("w01.first_commit", hint="git init, configure user.name/email in the repo, git add README.md, git commit -m '...'.")
def _(answer):
    repo = _repo(answer)
    commits = _commits(repo)
    assert commits, "the repository has no commits yet"
    files = _git(repo, "ls-files").split()
    assert "README.md" in files, "README.md is not tracked by Git: did you `git add` it before committing?"


@exercise("w01.three_commits", hint="Make two more small changes, each followed by git add and git commit with a clear message.")
def _(answer):
    repo = _repo(answer)
    commits = _commits(repo)
    assert len(commits) >= 3, f"the repository has {len(commits)} commit(s); make at least 3"
    for line in commits:
        msg = line.split(" ", 1)[1] if " " in line else ""
        assert len(msg.strip()) >= 5, f"commit message {msg!r} is too short to explain the change"
    status = _git(repo, "status", "--porcelain")
    assert not status.strip(), "you have uncommitted changes; commit (or discard) them so the working tree is clean"


@exercise("w01.gitignore", hint="Add a line `data/` to .gitignore, commit .gitignore, and do not `git add -f` the data file.")
def _(answer):
    repo = _repo(answer)
    gi = repo / ".gitignore"
    assert gi.is_file(), ".gitignore does not exist in the repository"
    assert ".gitignore" in _git(repo, "ls-files").split(), ".gitignore exists but is not committed"
    assert (repo / "data" / "big.csv").is_file(), "data/big.csv is missing: re-run the cell that creates it"
    tracked = _git(repo, "ls-files").split()
    assert "data/big.csv" not in tracked, "data/big.csv is tracked by Git; it should be ignored"
    ignored = subprocess.run(["git", "-C", str(repo), "check-ignore", "data/big.csv"], capture_output=True, text=True)
    assert ignored.returncode == 0, "Git does not ignore data/big.csv: check the pattern in .gitignore"


@exercise("w01.feature_branch", hint="git switch -c feature, commit there, git switch main, git merge feature.")
def _(answer):
    repo = _repo(answer)
    branches = _git(repo, "branch", "--format=%(refname:short)").split()
    assert "feature" in branches, "there is no branch called feature"
    current = _git(repo, "branch", "--show-current").strip()
    assert current == "main", f"you are on {current!r}; switch back to main after merging"
    only_feature = _git(repo, "log", "--format=%H", "main..feature").split()
    assert not only_feature, "feature has commits that are not in main: merge feature into main"
    tracked = _git(repo, "ls-tree", "-r", "--name-only", "main").split()
    assert "feature.txt" in tracked, "main does not contain feature.txt: commit it on feature, then merge"
    first = _git(repo, "log", "--format=%H", "--diff-filter=A", "--", "feature.txt").split()
    assert first, "feature.txt was never committed"


@exercise("w01.restore_file", hint="git restore README.md brings back the committed version.")
def _(answer):
    repo = _repo(answer)
    p = repo / "README.md"
    assert p.is_file(), "README.md is still missing"
    committed = _git(repo, "show", "HEAD:README.md")
    assert p.read_text() == committed, "README.md differs from the committed version"


register_quiz("w01.03_q1", "b",
              "`git add` copies the change into the staging area; only `git commit` records a snapshot in history.",
              {"a": "After add, nothing is in history yet: a commit is still needed.",
               "c": "add does not talk to GitHub; push does.",
               "d": "add does not create a branch."})
register_quiz("w01.03_q2", "d",
              "A commit is a snapshot of the whole project plus a message and a pointer to its parent.",
              {"a": "Commits are local until you push them.",
               "b": "Git stores snapshots, not only the lines you changed (it shows diffs, but stores snapshots).",
               "c": "Commits are permanent records; you add new commits rather than editing old ones."})
register_quiz("w01.03_q3", "c",
              "Data files, secrets and generated outputs belong in .gitignore: they are large, private, or reproducible.",
              {"a": "Source code is exactly what Git is for.",
               "b": "requirements.txt must be committed so others can install the same packages.",
               "d": "README.md is how people learn about the project; it must be committed."})
register_quiz("w01.03_q4", "a",
              "A pull request asks teammates to review a branch before it is merged into main.",
              {"b": "Pulling downloads; a pull request is a review request on the hosting site.",
               "c": "It does not delete anything.",
               "d": "Pull requests are a GitHub (and GitLab, etc.) feature built on top of Git branches."})
register_quiz("w01.03_q5", "b",
              "`|` sends one command's output into the next command's input, so small tools combine into a pipeline.",
              {"a": "That is `>`, which writes output to a file.",
               "c": "`|` does not run commands in parallel for speed; it connects them.",
               "d": "It is not a comment."})


# ============================================================================ 04 Lab: data utility
def _lab_files(tmp: Path) -> dict[str, Path]:
    ok = _write(tmp, "ok.csv", "id,name,age,signup_date\n1,Aru,31,2024-03-01\n2,Timur,45,2023-11-20\n")
    messy = _write(tmp, "messy.csv",
                   "id,name,age,signup_date\n1,Aru,31,2024-03-01\n2,,45,2023-11-20\n"
                   "3,Dana,abc,2024-01-05\n1,Ali,22,2024-13-01\n4,Saule,,2024-02-29\n")
    empty = _write(tmp, "empty.csv", "id,name,age,signup_date\n")
    return {"ok": ok, "messy": messy, "empty": empty}


SCHEMA = {"id": "int", "name": "str", "age": "int", "signup_date": "date"}


@exercise("w01.lab_load_rows", hint="csv.DictReader over the opened file; list(...) of the rows.")
def _(fn):
    with tempfile.TemporaryDirectory() as tmp:
        f = _lab_files(Path(tmp))
        rows = fn(f["ok"])
        assert isinstance(rows, list) and len(rows) == 2, "ok.csv has 2 data rows"
        assert rows[0] == {"id": "1", "name": "Aru", "age": "31", "signup_date": "2024-03-01"}, \
            "each row should be a dict of strings keyed by the header"
        assert fn(f["empty"]) == [], "a file with only a header gives an empty list"


@exercise("w01.lab_missing", hint="Row numbers start at 1 for the first data row; a value is missing if it is '' after strip().")
def _(fn):
    rows = [{"a": "1", "b": ""}, {"a": " ", "b": "x"}, {"a": "2", "b": "y"}]
    got = fn(rows, ["a", "b"])
    assert sorted(got) == [(1, "b"), (2, "a")], f"expected problems at (1, 'b') and (2, 'a'), got {got}"
    assert fn(rows, ["a"]) == [(2, "a")], "only check the columns you were asked about"
    assert fn([], ["a"]) == [], "no rows, no problems"


@exercise("w01.lab_type_problems", hint="For each column in the schema, try int(), or date.fromisoformat(); skip empty values.")
def _(fn):
    rows = [{"n": "3", "d": "2024-02-29"}, {"n": "x", "d": "2024-13-01"}, {"n": "", "d": ""}, {"n": "4.5", "d": "2023-02-29"}]
    got = sorted(fn(rows, {"n": "int", "d": "date"}))
    assert got == [(2, "d"), (2, "n"), (4, "d"), (4, "n")], f"expected type problems in rows 2 and 4, got {got}"
    assert fn([{"s": "anything"}], {"s": "str"}) == [], "a 'str' column accepts any text"


@exercise("w01.lab_duplicates", hint="Remember the first row number for each key value; report later rows with the same value.")
def _(fn):
    rows = [{"id": "1"}, {"id": "2"}, {"id": "1"}, {"id": "1"}, {"id": "3"}]
    assert fn(rows, "id") == [(3, "1"), (4, "1")], "report every repeat (row number, value) after the first occurrence"
    assert fn([{"id": "a"}], "id") == [], "a single row has no duplicates"


@exercise("w01.lab_validate", hint="Combine the three checks; 'ok' is True only when there are no problems at all.")
def _(fn):
    with tempfile.TemporaryDirectory() as tmp:
        f = _lab_files(Path(tmp))
        good = fn(f["ok"], SCHEMA, "id")
        assert good["rows"] == 2 and good["ok"] is True and good["problems"] == [], "ok.csv should validate cleanly"
        bad = fn(f["messy"], SCHEMA, "id")
        assert bad["rows"] == 5 and bad["ok"] is False, "messy.csv has 5 rows and is not ok"
        kinds = sorted(p["kind"] for p in bad["problems"])
        assert kinds == ["duplicate", "missing", "missing", "type", "type"], \
            f"messy.csv should give 2 missing, 2 type and 1 duplicate problem; got {kinds}"
        assert all({"kind", "row", "column"} <= set(p) for p in bad["problems"]), \
            "each problem needs the keys kind, row and column"


@exercise("w01.lab_report", hint="json.dumps(report, indent=2) into the file; create the parent folder first.")
def _(fn):
    with tempfile.TemporaryDirectory() as tmp:
        report = {"rows": 1, "ok": True, "problems": []}
        target = Path(tmp) / "out" / "report.json"
        fn(report, target)
        assert target.is_file(), "the report file was not written (does the function create the folder?)"
        assert json.loads(target.read_text()) == report, "the file must contain the report as JSON"


@exercise("w01.lab_repo", hint="The cells above write validator.py and commit it; check `git log` in the lab repo.")
def _(answer):
    repo = _repo(answer)
    files = _git(repo, "ls-files").split()
    assert "validator.py" in files, "validator.py is not committed in the lab repository"
    assert ".gitignore" in files, "commit a .gitignore too (reports and data should not be tracked)"
    assert len(_commits(repo)) >= 2, "make at least two commits (first version, then the improved one)"
    assert not _git(repo, "status", "--porcelain").strip(), "the lab repository has uncommitted changes"
    code = (repo / "validator.py").read_text()
    for name in ("load_rows", "missing_values", "type_problems", "duplicates", "validate"):
        assert f"def {name}" in code, f"validator.py does not define {name}()"


register_quiz("w01.04_q1", "c",
              "Validation at the start of a pipeline turns bad input into a clear report instead of a confusing "
              "error three steps later (or, worse, a silently wrong model).",
              {"a": "Validation does not make code faster.",
               "b": "It complements tests: tests check your code, validation checks the data.",
               "d": "Bad rows still have to be handled; validation tells you which and why."})
register_quiz("w01.04_q2", "a",
              "Returning a list of problems lets the caller decide what to do (stop, drop rows, alert); raising on the "
              "first problem hides the rest.",
              {"b": "Printing leaves nothing for the program to act on.",
               "c": "Fixing data silently is how wrong numbers reach a report.",
               "d": "Some problems are worth stopping for, but you still want to see all of them first."})
register_quiz("w01.04_q3", "d",
              "Small, separately tested functions are easy to reuse, test and combine; one big function is not.",
              {"a": "Speed is not the reason.",
               "b": "Python has no such limit.",
               "c": "Graders are a course device; the design is what teams do anyway."})
register_quiz("w01.04_q4", "b",
              "Committing the code (not the data or the reports) gives you a history to return to and a way to share.",
              {"a": "Data and generated reports should be ignored, not committed.",
               "c": "Git does not run your code.",
               "d": "A commit is local until you push it to GitHub."})
