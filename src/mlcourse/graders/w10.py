"""Week 10 graders: VS Code and a local setup, Docker, GitHub Actions (notebooks 37-40).

Nothing here needs Docker, a network or GitHub. Three kinds of exercise:
* functions (parsers, small simulators, linters), run on several inputs and edge cases and compared with an
  independent reference written here;
* files as text (requirements.txt, .gitignore, .dockerignore, settings.json, a Dockerfile, a workflow YAML),
  checked for *behaviour*: which paths a pattern file ignores, which rules a Dockerfile follows, what a workflow
  runs and in what order; never one exact text;
* tests the student writes (the lab), run against a correct app (they must pass) and buggy apps (they must fail).
"""
from __future__ import annotations

import importlib.util
import json
import random
import re
import shlex
import sys
import types
from pathlib import Path, PurePosixPath, PureWindowsPath

from mlcourse.grader import exercise, register_quiz

_REFERENCES: dict = {}
_NOTED: set = set()


def _ref(fn):
    _REFERENCES[fn.__name__.lstrip("_")] = fn
    return fn


def use(fn, *args, **kwargs):
    """Call your function `fn`; if it is not written yet, use the course's reference version (and say so)."""
    try:
        return fn(*args, **kwargs)
    except NotImplementedError:
        name = getattr(fn, "__name__", "")
        if name not in _REFERENCES:
            raise
        if name not in _NOTED:
            _NOTED.add(name)
            print(f"(note: `{name}` is not finished yet, so the course's reference version was used here. "
                  "Come back to that exercise.)")
        return _REFERENCES[name](*args, **kwargs)


def work_dir() -> Path:
    """The folder where this week's files are written: /content/work in Colab, <course>/work locally."""
    if "google.colab" in sys.modules:
        path = Path("/content/work")
    else:
        from mlcourse.paths import repo_root
        path = repo_root(Path(__file__).resolve().parent) / "work"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _text(answer, what: str) -> str:
    """Accept a string or a path to a file; refuse starters."""
    if isinstance(answer, Path):
        if not answer.is_file():
            raise AssertionError(f"the file {answer} does not exist: did you run the %%writefile cell?")
        answer = answer.read_text(encoding="utf-8")
    if not isinstance(answer, str):
        raise AssertionError(f"the {what} should be text (a string), got {type(answer).__name__}")
    if "YOUR" in answer and "HERE" in answer:
        raise NotImplementedError
    if not answer.strip():
        raise AssertionError(f"the {what} is empty")
    return answer


def _choices(answer, expected: dict, messages: dict, what: str = "answer") -> None:
    if not isinstance(answer, dict):
        raise AssertionError(f"the {what} should be a dict with keys {sorted(expected, key=str)}")
    missing = [k for k in expected if k not in answer]
    if missing:
        raise AssertionError(f"the {what} is missing the key(s) {missing}")
    for k, v in expected.items():
        got = answer[k]
        if isinstance(got, str):
            got = got.strip().lower()
        if got in ("?", "", None):
            raise AssertionError(f"`{k}` is not filled in yet")
        if got != v:
            raise AssertionError(f"`{k}` is not right: {messages[k]}")


# =========================================================================== notebook 37: local setup
def _norm_cmd(s: str) -> str:
    return re.sub(r"\s+", " ", str(s).strip()).lower()


ACTIVATE = {
    "linux": {"source .venv/bin/activate", ". .venv/bin/activate"},
    "macos": {"source .venv/bin/activate", ". .venv/bin/activate"},
    "windows_powershell": {r".venv\scripts\activate.ps1", r".\.venv\scripts\activate.ps1",
                           r"& .venv\scripts\activate.ps1", r"& .\.venv\scripts\activate.ps1",
                           ".venv/scripts/activate.ps1", "./.venv/scripts/activate.ps1"},
    "windows_cmd": {r".venv\scripts\activate.bat", r".venv\scripts\activate", r".\.venv\scripts\activate.bat",
                    r".\.venv\scripts\activate"},
}
ACTIVATE_MSG = {
    "linux": "on Linux the activation script is in the venv's `bin` folder and is run with `source`.",
    "macos": "macOS works like Linux here (a `bin` folder, run with `source`).",
    "windows_powershell": "on Windows the venv has a `Scripts` folder; PowerShell runs the `.ps1` script.",
    "windows_cmd": "the classic Command Prompt runs the batch file (`.bat`) in the `Scripts` folder.",
}


@exercise("w10.activate", hint="Look at the table in section 2: Linux and macOS share one form, Windows has two.")
def _t_activate(answer):
    if not isinstance(answer, dict):
        raise AssertionError("the answer should be a dict with keys linux, macos, windows_powershell, windows_cmd")
    for k, ok in ACTIVATE.items():
        if k not in answer:
            raise AssertionError(f"the key {k!r} is missing")
        got = _norm_cmd(answer[k])
        if got in ("", "?"):
            raise AssertionError(f"`{k}` is not filled in yet")
        if got not in ok:
            raise AssertionError(f"`{k}` is not a command that activates `.venv`: {ACTIVATE_MSG[k]}")


@_ref
def _uses_project_venv(python_path: str, project_dir: str) -> bool:
    win = "\\" in python_path or "\\" in project_dir or re.match(r"^[A-Za-z]:", python_path or "")
    P = PureWindowsPath if win else PurePosixPath
    py, proj = P(python_path), P(project_dir)
    venv = proj / ".venv"
    if win:
        py_parts = [p.lower() for p in py.parts]
        venv_parts = [p.lower() for p in venv.parts]
    else:
        py_parts, venv_parts = list(py.parts), list(venv.parts)
    return len(py_parts) > len(venv_parts) and py_parts[:len(venv_parts)] == venv_parts


@exercise("w10.in_venv", hint="Build the path of the project's .venv folder, then ask whether the interpreter path "
                              "starts with it, part by part (pathlib's .parts). Windows paths ignore case.")
def _t_in_venv(fn):
    cases = [
        ("/home/ana/shop/.venv/bin/python", "/home/ana/shop", True),
        ("/home/ana/shop/.venv/bin/python3.12", "/home/ana/shop/", True),
        ("/usr/bin/python3", "/home/ana/shop", False),
        ("/home/ana/shop/venv/bin/python", "/home/ana/shop", False),
        ("/home/ana/other/.venv/bin/python", "/home/ana/shop", False),
        ("/home/ana/shop2/.venv/bin/python", "/home/ana/shop", False),
        ("/home/ana/shop/.venv", "/home/ana/shop", False),
        ("/opt/homebrew/bin/python3", "/Users/ana/shop", False),
        ("/Users/ana/shop/.venv/bin/python", "/Users/ana/shop", True),
        (r"C:\Users\Ana\shop\.venv\Scripts\python.exe", r"C:\Users\Ana\shop", True),
        (r"c:\users\ana\shop\.venv\scripts\python.exe", r"C:\Users\Ana\shop", True),
        (r"C:\Users\Ana\AppData\Local\Programs\Python\Python312\python.exe", r"C:\Users\Ana\shop", False),
    ]
    for py, proj, want in cases:
        got = fn(py, proj)
        if not isinstance(got, bool):
            raise AssertionError(f"return True or False, got {got!r}")
        if got != want:
            raise AssertionError(f"uses_project_venv({py!r}, {proj!r}) returned {got}; "
                                 f"{'it is inside the project' + chr(39) + 's .venv' if want else 'it is not inside this project' + chr(39) + 's .venv'}"
                                 + (" (Windows paths are not case-sensitive)" if "\\" in py and want else ""))


@_ref
def _which(command: str, path_value: str, sep: str, files: set):
    for d in path_value.split(sep):
        d = d.rstrip("/")
        if not d:
            continue
        candidate = f"{d}/{command}"
        if candidate in files:
            return candidate
    return None


@exercise("w10.which", hint="Split PATH on the separator, walk the folders in order, and return the first "
                            "folder/command that is in `files`. Skip empty entries; drop a trailing '/'.")
def _t_which(fn):
    files = {"/usr/bin/python3", "/usr/bin/git", "/home/a/p/.venv/bin/python3", "/home/a/p/.venv/bin/pytest",
             "/opt/tools/git"}
    cases = [
        ("python3", "/home/a/p/.venv/bin:/usr/bin", "/home/a/p/.venv/bin/python3"),
        ("python3", "/usr/bin:/home/a/p/.venv/bin", "/usr/bin/python3"),
        ("pytest", "/usr/bin:/home/a/p/.venv/bin", "/home/a/p/.venv/bin/pytest"),
        ("git", "/opt/tools/:/usr/bin", "/opt/tools/git"),
        ("docker", "/usr/bin:/opt/tools", None),
        ("git", "::/usr/bin", "/usr/bin/git"),
        ("python3", "", None),
    ]
    for cmd, pv, want in cases:
        got = fn(cmd, pv, ":", files)
        if got != want:
            raise AssertionError(f"which({cmd!r}, {pv!r}, ':', files) returned {got!r}, expected {want!r}. "
                                 "The FIRST folder on PATH that has the command wins.")
    got = fn("python3", r"/usr/bin;/home/a/p/.venv/bin", ";", files)
    if got != "/usr/bin/python3":
        raise AssertionError("with sep=';' (the Windows separator) the PATH must be split on ';'")


def _req_name(spec: str) -> str:
    name = re.split(r"[\s\[<>=!~;@]", spec, maxsplit=1)[0]
    return name.lower().replace("_", "-").replace(".", "-")


@_ref
def _parse_requirements(text: str) -> dict:
    out = {}
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or line.startswith("-"):
            continue
        line = line.split(";", 1)[0].strip()
        name = _req_name(line)
        m = re.search(r"==\s*([^\s,;]+)", line)
        version = m.group(1) if (m and "," not in line.split("==", 1)[1]) else None
        if m and "===" in line:
            version = None
        out[name] = version
    return out


@exercise("w10.parse_requirements",
          hint="Per line: cut everything after '#', skip blank lines and option lines starting with '-', drop an "
               "environment marker after ';', drop extras in [...], and keep a version only for an exact '=='.")
def _t_parse_requirements(fn):
    cases = [
        ("fastapi==0.110.0\nuvicorn==0.29.0\n", {"fastapi": "0.110.0", "uvicorn": "0.29.0"}),
        ("# web\nfastapi==0.110.0  # the API\n\n   \npandas>=2.1\n", {"fastapi": "0.110.0", "pandas": None}),
        ("-r requirements.txt\n--index-url https://example.org/simple\npytest==8.2.0\n", {"pytest": "8.2.0"}),
        ("Scikit_Learn==1.5.0\n", {"scikit-learn": "1.5.0"}),
        ("uvicorn[standard]==0.29.0\n", {"uvicorn": "0.29.0"}),
        ("numpy==1.26.4 ; python_version < '3.13'\n", {"numpy": "1.26.4"}),
        ("requests\nnumpy>=1.26,<2\n", {"requests": None, "numpy": None}),
        ("", {}),
    ]
    for text, want in cases:
        got = fn(text)
        if not isinstance(got, dict):
            raise AssertionError(f"return a dict, got {type(got).__name__}")
        if got != want:
            raise AssertionError(f"for the file\n{text!r}\nexpected {want}, got {got}")


@_ref
def _unpinned(text: str) -> list:
    return sorted(n for n, v in _parse_requirements(text).items() if v is None)


@exercise("w10.unpinned", hint="Reuse parse_requirements (through use(...)) and keep the names whose version is None.")
def _t_unpinned(fn):
    cases = [
        ("fastapi==0.110.0\npandas>=2.1\nrequests\n", ["pandas", "requests"]),
        ("a==1\nb==2\n", []),
        ("# all comments\n", []),
        ("Zeta\nalpha~=1.2\nmid==3\n", ["alpha", "zeta"]),
    ]
    for text, want in cases:
        got = fn(text)
        if not isinstance(got, list):
            raise AssertionError(f"return a list, got {type(got).__name__}")
        if got != want:
            raise AssertionError(f"for\n{text!r}\nexpected {want}, got {got} (sorted, normalised names)")


@exercise("w10.settings_json",
          hint="Three settings: the interpreter path inside .venv, pytest enabled, and pytest's arguments as a list.")
def _t_settings(answer):
    text = _text(answer, "settings.json")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as err:
        raise AssertionError(f"this is not valid JSON ({err.msg} at line {err.lineno}): check quotes (double "
                             "quotes only), commas between entries and no comma after the last one")
    if not isinstance(data, dict):
        raise AssertionError("settings.json should be one JSON object { ... }")
    interp = data.get("python.defaultInterpreterPath")
    if not isinstance(interp, str) or ".venv" not in interp.replace("\\", "/"):
        raise AssertionError("set python.defaultInterpreterPath to the interpreter inside the project's .venv")
    if data.get("python.testing.pytestEnabled") is not True:
        raise AssertionError("pytest is not enabled: python.testing.pytestEnabled should be true (JSON true, "
                             "no quotes)")
    if data.get("python.testing.unittestEnabled") is True:
        raise AssertionError("turn the unittest runner off when you use pytest (or leave the key out)")
    args = data.get("python.testing.pytestArgs")
    if not isinstance(args, list) or "tests" not in [str(a).strip("/") for a in args]:
        raise AssertionError("python.testing.pytestArgs should be a list that includes the tests folder")


def _pattern_regex(pattern: str) -> str:
    out, i = "", 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out += "(?:.*/)?"
            i += 3
        elif pattern.startswith("**", i):
            out += ".*"
            i += 2
        elif pattern[i] == "*":
            out += "[^/]*"
            i += 1
        elif pattern[i] == "?":
            out += "[^/]"
            i += 1
        else:
            out += re.escape(pattern[i])
            i += 1
    return out


def _ignored(patterns: list[str], path: str, gitignore: bool) -> bool:
    """Minimal .gitignore / .dockerignore semantics: last matching pattern wins, '!' re-includes, a pattern that
    matches a folder covers everything inside it. In .gitignore a pattern with no inner '/' matches at any depth;
    in .dockerignore every pattern is anchored at the build-context root (so use **/ for any depth)."""
    parts = path.split("/")
    prefixes = ["/".join(parts[:i]) for i in range(1, len(parts) + 1)]
    result = False
    for raw in patterns:
        p = raw.strip()
        if not p or p.startswith("#"):
            continue
        neg = p.startswith("!")
        if neg:
            p = p[1:]
        if p.startswith("./"):
            p = p[2:]
        dir_only = p.endswith("/")
        p = p.strip("/") if gitignore else p.lstrip("/").rstrip("/")
        if gitignore and "/" not in p and not raw.strip().lstrip("!").startswith("/"):
            p = "**/" + p
        rx = re.compile(_pattern_regex(p))
        hit = False
        for k, pre in enumerate(prefixes):
            is_dir = k < len(prefixes) - 1
            if dir_only and not is_dir:
                continue
            if rx.fullmatch(pre):
                hit = True
                break
        if hit:
            result = not neg
    return result


GITIGNORE_YES = [".venv/bin/python", ".venv/Lib/site-packages/x.py", "__pycache__/a.cpython-312.pyc",
                 "src/shop/__pycache__/m.cpython-312.pyc", ".ipynb_checkpoints/a-checkpoint.ipynb",
                 "notebooks/.ipynb_checkpoints/b-checkpoint.ipynb", ".env", "service/.env", ".pytest_cache/v/x"]
GITIGNORE_NO = ["requirements.txt", "src/shop/main.py", "tests/test_main.py", ".env.example", "README.md",
                "notebooks/explore.ipynb", ".vscode/settings.json", ".gitignore", "src/shop/environment.py"]
GITIGNORE_WHY = {
    ".venv": "the virtual environment (.venv/) is rebuilt from requirements.txt; never commit it",
    "__pycache__": "Python's byte-code caches (__pycache__/) appear in every package folder, at any depth",
    ".ipynb_checkpoints": "Jupyter's autosave folders (.ipynb_checkpoints/) appear next to any notebook",
    ".env": "a .env file holds secrets, wherever it is",
    ".pytest_cache": "pytest's cache folder is machine-specific",
}


def _check_ignore_file(text: str, yes: list, no: list, why: dict, gitignore: bool, what: str) -> None:
    patterns = text.splitlines()
    for path in yes:
        if not _ignored(patterns, path, gitignore):
            key = next((k for k in why if k in path), "")
            raise AssertionError(f"`{path}` is not ignored by your {what}: {why.get(key, 'it should be')}")
    for path in no:
        if _ignored(patterns, path, gitignore):
            raise AssertionError(f"your {what} also ignores `{path}`, which the project needs: make that "
                                 "pattern narrower")


@exercise("w10.gitignore", hint="Folder patterns end in '/'. A pattern with no '/' in the middle matches at any "
                                "depth. Is `.env*` too wide?")
def _t_gitignore(answer):
    _check_ignore_file(_text(answer, ".gitignore"), GITIGNORE_YES, GITIGNORE_NO, GITIGNORE_WHY, True, ".gitignore")


DIAGNOSE_LABELS = ["install_in_venv", "python_not_on_path", "use_a_venv", "wrong_folder", "powershell_policy",
                   "ssh_key", "unknown"]


@_ref
def _diagnose(message: str) -> str:
    m = message.lower()
    if "no module named" in m:
        return "install_in_venv"
    if "externally-managed-environment" in m or "externally managed" in m:
        return "use_a_venv"
    if "running scripts is disabled" in m:
        return "powershell_policy"
    if "not a git repository" in m:
        return "wrong_folder"
    if "permission denied (publickey)" in m:
        return "ssh_key"
    if ("python" in m or "py" in m.split()) and ("not recognized" in m or "command not found" in m
                                                  or "not found" in m):
        return "python_not_on_path"
    return "unknown"


@exercise("w10.diagnose", hint="Lower-case the message, then look for the tell-tale phrase of each error from the "
                               "table in section 5. Anything else is 'unknown'.")
def _t_diagnose(fn):
    cases = [
        ("ModuleNotFoundError: No module named 'pandas'", "install_in_venv"),
        ("ModuleNotFoundError: No module named 'fastapi.testclient'", "install_in_venv"),
        ("'python' is not recognized as an internal or external command,\noperable program or batch file.",
         "python_not_on_path"),
        ("bash: python3: command not found", "python_not_on_path"),
        ("zsh: command not found: python", "python_not_on_path"),
        ("error: externally-managed-environment\n\n× This environment is externally managed", "use_a_venv"),
        ("fatal: not a git repository (or any of the parent directories): .git", "wrong_folder"),
        (r"File C:\Users\ana\shop\.venv\Scripts\Activate.ps1 cannot be loaded because running scripts is "
         "disabled on this system.", "powershell_policy"),
        ("git@github.com: Permission denied (publickey).\nfatal: Could not read from remote repository.", "ssh_key"),
        ("ValueError: could not convert string to float: 'abc'", "unknown"),
        ("", "unknown"),
    ]
    for msg, want in cases:
        got = fn(msg)
        if got not in DIAGNOSE_LABELS:
            raise AssertionError(f"return one of {DIAGNOSE_LABELS}, got {got!r}")
        if got != want:
            first = msg.splitlines()[0] if msg else "(an empty message)"
            raise AssertionError(f"the message starting {first[:70]!r} was diagnosed as {got!r}; read it again")


@_ref
def _median_order_value(values):
    if len(values) == 0:
        raise ValueError("no orders")
    s = sorted(values)
    n = len(s)
    mid = n // 2
    return float(s[mid]) if n % 2 else (s[mid - 1] + s[mid]) / 2


@exercise("w10.debug_fix", hint="Two bugs: which elements are averaged when the length is even, and what happens to "
                                "the caller's list. Watch `values` in the debugger (or print it) before and after.")
def _t_debug_fix(fn):
    import statistics
    rng = random.Random(10)
    for n in [1, 2, 3, 4, 5, 6, 9, 10]:
        vals = [round(rng.uniform(1, 200), 2) for _ in range(n)]
        before = list(vals)
        got = fn(vals)
        if vals != before:
            raise AssertionError("your function changed the list it was given (the caller's data): sort a copy")
        want = statistics.median(before)
        if not isinstance(got, (int, float)) or abs(got - want) > 1e-9:
            raise AssertionError(f"for {n} values the median is wrong (got {got}); check the even-length case")
    try:
        fn([])
    except ValueError:
        pass
    except Exception as err:
        raise AssertionError(f"an empty list should raise ValueError, not {type(err).__name__}")
    else:
        raise AssertionError("an empty list should raise ValueError (there is no median of nothing)")


# =========================================================================== notebook 38: Docker
@_ref
def _parse_dockerfile(text: str) -> list:
    out, buf = [], ""
    for raw in text.splitlines():
        line = raw.strip()
        if not buf and (not line or line.startswith("#")):
            continue
        if buf and line.startswith("#"):
            continue
        if line.endswith("\\"):
            buf += line[:-1].strip() + " "
            continue
        buf += line
        buf = buf.strip()
        if buf:
            parts = buf.split(None, 1)
            out.append((parts[0].upper(), parts[1].strip() if len(parts) > 1 else ""))
        buf = ""
    if buf.strip():
        parts = buf.strip().split(None, 1)
        out.append((parts[0].upper(), parts[1].strip() if len(parts) > 1 else ""))
    return out


@exercise("w10.parse_dockerfile",
          hint="Skip blank and '#' lines; while a line ends with a backslash, keep joining the next line; split the "
               "joined line once on whitespace into (INSTRUCTION in upper case, the rest).")
def _t_parse_dockerfile(fn):
    cases = [
        ("FROM python:3.12-slim\nWORKDIR /app\n", [("FROM", "python:3.12-slim"), ("WORKDIR", "/app")]),
        ("# comment\n\nfrom python:3.12-slim\n  run   pip install x  \n",
         [("FROM", "python:3.12-slim"), ("RUN", "pip install x")]),
        ("RUN apt-get update && \\\n    apt-get install -y curl\nUSER app\n",
         [("RUN", "apt-get update && apt-get install -y curl"), ("USER", "app")]),
        ('CMD ["uvicorn", "app.main:app"]\n', [("CMD", '["uvicorn", "app.main:app"]')]),
        ("RUN a \\\n  # a comment inside\n  && b\n", [("RUN", "a && b")]),
        ("", []),
    ]
    for text, want in cases:
        got = fn(text)
        if not isinstance(got, list) or any(not isinstance(t, tuple) or len(t) != 2 for t in got):
            raise AssertionError("return a list of (instruction, arguments) tuples")
        got = [(a, re.sub(r"\s+", " ", b)) for a, b in got]
        if got != want:
            raise AssertionError(f"for the Dockerfile\n{text!r}\nexpected {want}\ngot      {got}")


@_ref
def _is_pinned(image: str) -> bool:
    image = image.strip()
    if "@sha256:" in image:
        return True
    last = image.rsplit("/", 1)[-1]
    if ":" not in last:
        return False
    tag = last.split(":", 1)[1]
    return bool(tag) and tag != "latest"


@exercise("w10.is_pinned", hint="A digest (@sha256:...) always pins. Otherwise look for ':' only in the LAST "
                                "'/'-separated part (a registry can have a port), and 'latest' is not a pin.")
def _t_is_pinned(fn):
    cases = [("python:3.12-slim", True), ("python", False), ("python:latest", False),
             ("python@sha256:" + "a" * 64, True), ("ghcr.io/acme/scorer:1.4.2", True),
             ("localhost:5000/scorer", False), ("localhost:5000/scorer:0.3", True), ("ubuntu:24.04", True),
             ("registry.example.com:443/team/img:latest", False)]
    for img, want in cases:
        got = fn(img)
        if got is not want:
            raise AssertionError(f"is_pinned({img!r}) returned {got!r}; it should be {want}")


@_ref
def _docker_run_args(image, ports=None, env=None, volume=None, detach=False, name=None):
    args = ["docker", "run", "--rm"]
    if detach:
        args.append("-d")
    if name:
        args += ["--name", name]
    for host, cont in (ports or {}).items():
        args += ["-p", f"{host}:{cont}"]
    for k, v in (env or {}).items():
        args += ["-e", f"{k}={v}"]
    if volume:
        args += ["-v", f"{volume[0]}:{volume[1]}"]
    args.append(image)
    return args


def _parse_run(args: list) -> dict:
    if not isinstance(args, list) or not all(isinstance(a, str) for a in args):
        raise AssertionError("return a list of strings, one per word of the command")
    if args[:2] != ["docker", "run"]:
        raise AssertionError("the command should start with 'docker', 'run'")
    out = {"rm": False, "d": False, "name": None, "p": [], "e": [], "v": [], "rest": []}
    i = 2
    while i < len(args):
        a = args[i]
        if a == "--rm":
            out["rm"] = True
        elif a in ("-d", "--detach"):
            out["d"] = True
        elif a in ("--name", "-p", "--publish", "-e", "--env", "-v", "--volume"):
            if i + 1 >= len(args):
                raise AssertionError(f"{a} needs a value after it")
            key = {"--name": "name", "-p": "p", "--publish": "p", "-e": "e", "--env": "e", "-v": "v",
                   "--volume": "v"}[a]
            if key == "name":
                out["name"] = args[i + 1]
            else:
                out[key].append(args[i + 1])
            i += 1
        elif a.startswith("-"):
            raise AssertionError(f"unexpected option {a!r}")
        else:
            out["rest"] = args[i:]
            break
        i += 1
    return out


@exercise("w10.docker_run_args", hint="Options (--rm, -d, --name, -p host:container, -e KEY=value, -v host:container) "
                                      "all come BEFORE the image name; the image is the last word.")
def _t_docker_run_args(fn):
    cases = [
        dict(image="scorer:0.1"),
        dict(image="scorer:0.1", ports={8080: 8000}),
        dict(image="scorer:0.1", ports={8080: 8000, 9090: 9000}, env={"LOG_LEVEL": "debug", "MODEL": "v2"}),
        dict(image="scorer:0.1", volume=("/home/ana/data", "/app/data"), detach=True, name="scorer"),
    ]
    for kw in cases:
        got = _parse_run(fn(**kw))
        if not got["rm"]:
            raise AssertionError("always add --rm so stopped containers are cleaned up")
        if got["rest"] != [kw["image"]]:
            raise AssertionError(f"the image should be the last word, after every option (case {kw})")
        if sorted(got["p"]) != sorted(f"{h}:{c}" for h, c in (kw.get("ports") or {}).items()):
            raise AssertionError(f"the port mappings are wrong for {kw}: each is -p HOST:CONTAINER")
        if sorted(got["e"]) != sorted(f"{k}={v}" for k, v in (kw.get("env") or {}).items()):
            raise AssertionError(f"the environment variables are wrong for {kw}: each is -e KEY=value")
        want_v = [f"{kw['volume'][0]}:{kw['volume'][1]}"] if kw.get("volume") else []
        if got["v"] != want_v:
            raise AssertionError(f"the volume is wrong for {kw}: -v HOST_FOLDER:CONTAINER_FOLDER")
        if got["d"] != bool(kw.get("detach")):
            raise AssertionError(f"-d (detach) should appear only when detach=True (case {kw})")
        if got["name"] != kw.get("name"):
            raise AssertionError(f"--name should appear only when a name is given (case {kw})")


PORT_ANSWERS = {"a": 9000, "b": "none", "c": 8000, "d": "none"}
PORT_MSG = {
    "a": "-p HOST:CONTAINER: your browser talks to the HOST side.",
    "b": "without -p, nothing on your computer is connected to the container's port.",
    "c": "the left number is the one you visit.",
    "d": "the server listens on 127.0.0.1 INSIDE the container, which only the container itself can reach.",
}


@exercise("w10.ports", hint="The host port is the LEFT side of -p. And 127.0.0.1 inside a container means 'only "
                            "this container'.")
def _t_ports(answer):
    if isinstance(answer, dict):
        answer = {k: (int(v) if isinstance(v, str) and v.strip().isdigit() else v) for k, v in answer.items()}
    _choices(answer, PORT_ANSWERS, PORT_MSG, "answer")


@_ref
def _to_exec_form(command: str) -> str:
    return json.dumps(shlex.split(command))


@exercise("w10.exec_form", hint="shlex.split understands quotes the way a shell does; json.dumps writes the list "
                               "with double quotes.")
def _t_exec_form(fn):
    cases = ["uvicorn app.main:app --host 0.0.0.0 --port 8000", "python -m pytest -q",
             "python -c 'print(\"hi\")'", "echo \"two words\" three", "gunicorn  -w 2   app:app"]
    for cmd in cases:
        got = fn(cmd)
        if not isinstance(got, str):
            raise AssertionError("return the exec form as a string, e.g. '[\"python\", \"app.py\"]'")
        try:
            parsed = json.loads(got)
        except json.JSONDecodeError:
            raise AssertionError(f"for {cmd!r} the result {got!r} is not a JSON array: Docker needs double quotes")
        if parsed != shlex.split(cmd):
            raise AssertionError(f"for {cmd!r} you produced {parsed}: quoted words must stay together and extra "
                                 "spaces must not create empty words")


def _cmd_list(args: str):
    try:
        v = json.loads(args)
    except json.JSONDecodeError:
        return None
    return v if isinstance(v, list) and all(isinstance(x, str) for x in v) else None


def _dockerfile_problems(text: str, need_healthcheck: bool = False, need_model: bool = False) -> list[str]:
    ins = _parse_dockerfile(text)
    names = [i for i, _ in ins]
    problems = []
    if not ins or names[0] not in ("FROM", "ARG"):
        return ["the Dockerfile must start with FROM (the base image)"]
    base = next(a for i, a in ins if i == "FROM").split()[0]
    if not _is_pinned(base):
        problems.append(f"the base image {base!r} is not pinned to a version")
    elif "slim" not in base and "alpine" not in base and "@sha256" not in base:
        problems.append(f"{base!r} is a full image (over 1 GB); use a -slim variant")
    if "WORKDIR" not in names:
        problems.append("set a WORKDIR so files do not land in the image's root folder")
    copies = [(k, a) for k, (i, a) in enumerate(ins) if i in ("COPY", "ADD")]
    pip = [k for k, (i, a) in enumerate(ins) if i == "RUN" and "pip install" in a]
    req_copy = [k for k, a in copies if _copy_sources(a) and all("requirements" in s for s in _copy_sources(a))]
    code_copy = [k for k, a in copies if k not in req_copy]
    if not pip:
        problems.append("there is no RUN pip install step for the dependencies")
    else:
        if not any("-r" in ins[k][1] and "requirements" in ins[k][1] for k in pip):
            problems.append("install the dependencies from requirements.txt (pip install -r requirements.txt)")
        if not req_copy or min(req_copy) > min(pip):
            problems.append("copy requirements.txt on its own BEFORE pip install, so that layer can be cached")
        if code_copy and min(code_copy) < min(pip):
            problems.append("the app code is copied before pip install: every code change would reinstall all "
                            "dependencies (copy requirements.txt, install, THEN copy the code)")
        if not all("--no-cache-dir" in ins[k][1] for k in pip):
            problems.append("pip keeps its download cache in the image: add --no-cache-dir")
    if not code_copy:
        problems.append("the app code is never copied into the image")
    elif need_model and not any("model" in a for _, a in copies if a):
        problems.append("the model file is never copied into the image")
    users = [k for k, (i, a) in enumerate(ins) if i == "USER"]
    if not users or ins[users[-1]][1].strip() in ("root", "0"):
        problems.append("the container runs as root: create a user and switch to it with USER")
    for i, a in ins:
        if i in ("ENV", "ARG"):
            for name in re.findall(r"([A-Za-z_][A-Za-z0-9_]*)\s*=", a) or a.split()[:1]:
                if re.search(r"KEY|TOKEN|SECRET|PASSWORD", name, re.I):
                    problems.append(f"{i} {name} looks like a secret baked into the image: pass it at run time")
    if "EXPOSE" not in names:
        problems.append("add EXPOSE with the port the server listens on (it documents the port)")
    cmds = [a for i, a in ins if i == "CMD"]
    if not cmds:
        problems.append("there is no CMD: the container would not know how to start the server")
    else:
        cmd = _cmd_list(cmds[-1])
        if cmd is None:
            problems.append("write CMD in exec form, a JSON list: CMD [\"uvicorn\", ...]")
        else:
            joined = " ".join(cmd)
            if "uvicorn" not in joined or "app.main:app" not in joined:
                problems.append("CMD should start uvicorn with the app object app.main:app")
            if "0.0.0.0" not in joined:
                problems.append("uvicorn must listen on --host 0.0.0.0, or nothing outside the container can "
                                "reach it")
            expose = [a for i, a in ins if i == "EXPOSE"]
            m = re.search(r"--port[ =](\d+)", joined)
            port = m.group(1) if m else "8000"
            if expose and port not in " ".join(expose):
                problems.append(f"EXPOSE says {expose[0]} but uvicorn listens on {port}")
        if users and ins.index(next(t for t in ins if t[0] == "CMD")) < users[-1]:
            pass
    if need_healthcheck:
        hc = [a for i, a in ins if i == "HEALTHCHECK"]
        if not hc:
            problems.append("add a HEALTHCHECK that calls /health")
        elif "/health" not in hc[0]:
            problems.append("the HEALTHCHECK should call the /health endpoint")
        elif re.search(r"\bcurl\b|\bwget\b", hc[0]):
            problems.append("python:*-slim images have no curl or wget: check /health with python -c and urllib")
    return problems


GOOD_38 = """FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ app/
RUN useradd --create-home appuser
USER appuser
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
"""


@exercise("w10.dockerfile", hint="Follow the six numbered steps of the Dockerfile in section 3, in that order.")
def _t_dockerfile(answer):
    problems = _dockerfile_problems(_text(answer, "Dockerfile"))
    if problems:
        more = f" (and {len(problems) - 1} more)" if len(problems) > 1 else ""
        raise AssertionError(problems[0] + more)


DOCKERIGNORE_YES = [".git/HEAD", ".git/objects/ab/cdef", ".venv/bin/python", "app/__pycache__/main.cpython-312.pyc",
                    "__pycache__/x.pyc", ".env", "notebooks/explore.ipynb", "tests/__pycache__/t.pyc"]
DOCKERIGNORE_NO = ["app/main.py", "app/__init__.py", "requirements.txt", "Dockerfile"]
DOCKERIGNORE_WHY = {
    ".git": "the .git history is large and not needed to run the app",
    ".venv": "your local virtual environment must not be copied (the image installs its own)",
    "__pycache__": "byte-code caches appear at any depth; in .dockerignore that needs **/ in front",
    ".env": "a .env file holds secrets and must never enter an image",
    "notebooks": "notebooks are not part of the service",
}


@exercise("w10.dockerignore", hint="Unlike .gitignore, every .dockerignore pattern starts at the project root: "
                                   "`__pycache__` only matches the top folder, `**/__pycache__` matches any depth.")
def _t_dockerignore(answer):
    _check_ignore_file(_text(answer, ".dockerignore"), DOCKERIGNORE_YES, DOCKERIGNORE_NO, DOCKERIGNORE_WHY, False,
                       ".dockerignore")


def _copy_sources(args: str) -> list[str]:
    a = _cmd_list(args)
    words = a if a is not None else args.split()
    words = [w for w in words if not w.startswith("--")]
    return words[:-1]


def _touches(sources: list[str], changed: set) -> bool:
    for s in sources:
        s = s.rstrip("/")
        if s in (".", "./", ""):
            if changed:
                return True
            continue
        for f in changed:
            if f == s or f.startswith(s + "/") or re.fullmatch(_pattern_regex(s), f):
                return True
    return False


@_ref
def _rebuilt_steps(instructions: list, changed: set) -> list:
    for k, (ins, args) in enumerate(instructions):
        if ins in ("COPY", "ADD") and _touches(_copy_sources(args), set(changed)):
            return list(range(k, len(instructions)))
    return []


@exercise("w10.rebuilt_steps", hint="Walk the steps in order. The first COPY/ADD whose sources include a changed file "
                                    "breaks the cache; it and EVERY step after it run again.")
def _t_rebuilt(fn):
    good = _parse_dockerfile(GOOD_38)
    slow = _parse_dockerfile("FROM python:3.12-slim\nWORKDIR /app\nCOPY . .\n"
                             "RUN pip install --no-cache-dir -r requirements.txt\nCMD [\"python\", \"app.py\"]\n")
    cases = [
        (good, {"app/main.py"}, [4, 5, 6, 7, 8]),
        (good, {"requirements.txt"}, [2, 3, 4, 5, 6, 7, 8]),
        (good, set(), []),
        (good, {"README.md"}, []),
        (slow, {"app.py"}, [2, 3, 4]),
        (slow, {"README.md"}, [2, 3, 4]),
        (_parse_dockerfile("FROM x:1\nCOPY a.txt b.txt ./\nRUN make\nCOPY src/ src/\n"), {"b.txt"}, [1, 2, 3]),
        (_parse_dockerfile("FROM x:1\nCOPY a.txt b.txt ./\nRUN make\nCOPY src/ src/\n"), {"src/x.py"}, [3]),
    ]
    for ins, changed, want in cases:
        got = fn(ins, changed)
        if list(got) != want:
            raise AssertionError(f"for the steps {[i for i, _ in ins]} with changed files {sorted(changed)} "
                                 f"expected re-run steps {want}, got {list(got)}")


@_ref
def _find_secrets(text: str) -> list:
    found = []
    for ins, args in _parse_dockerfile(text):
        if ins not in ("ENV", "ARG"):
            continue
        pairs = re.findall(r"([A-Za-z_][A-Za-z0-9_]*)=(\"[^\"]*\"|'[^']*'|\S*)", args)
        if not pairs and ins == "ENV":
            bits = args.split(None, 1)
            pairs = [(bits[0], bits[1] if len(bits) > 1 else "")]
        for name, value in pairs:
            if value.strip("\"'") and re.search(r"KEY|TOKEN|SECRET|PASSWORD", name, re.I):
                found.append(name)
    return found


@exercise("w10.find_secrets", hint="Use parse_dockerfile (through use(...)). Look at ENV and ARG only. Forms: "
                                   "NAME=value (several per line), the old `ENV NAME value`, and ARG NAME with no "
                                   "value (not a secret yet).")
def _t_find_secrets(fn):
    cases = [
        ("FROM a:1\nENV LOG_LEVEL=info\n", []),
        ("FROM a:1\nENV API_KEY=abc123\n", ["API_KEY"]),
        ("FROM a:1\nENV LOG_LEVEL=info DB_PASSWORD=hunter2 PORT=8000\n", ["DB_PASSWORD"]),
        ("FROM a:1\nENV github_token ghp_xxx\n", ["github_token"]),
        ("FROM a:1\nARG HF_TOKEN\nARG SECRET_SALT=pepper\n", ["SECRET_SALT"]),
        ("FROM a:1\nRUN echo API_KEY=abc\n", []),
        ("FROM a:1\nENV MONKEY=banana\nENV TOKEN_URL=\"\"\n", ["MONKEY"]),
    ]
    for text, want in cases:
        got = fn(text)
        if not isinstance(got, list):
            raise AssertionError("return a list of variable names")
        if got != want:
            raise AssertionError(f"for\n{text}expected {want}, got {got}")


# =========================================================================== notebook 39: GitHub Actions
def _yaml(text: str):
    import yaml
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as err:
        mark = getattr(err, "problem_mark", None)
        where = f" near line {mark.line + 1}" if mark else ""
        raise AssertionError(f"this is not valid YAML{where}: check the indentation (spaces, never tabs) and "
                             "the colons")


@_ref
def _triggers(workflow_text: str) -> list:
    import yaml
    data = yaml.safe_load(workflow_text) or {}
    on = data.get("on", data.get(True))
    if on is None:
        return []
    if isinstance(on, str):
        return [on]
    if isinstance(on, list):
        return sorted(on)
    return sorted(on)


@exercise("w10.triggers", hint="yaml.safe_load reads the key `on` as the boolean True (YAML 1.1). Look up both. "
                               "Then handle the three shapes: a string, a list, or a mapping.")
def _t_triggers(fn):
    cases = [
        ("on: push\njobs: {}\n", ["push"]),
        ("on: [push, pull_request]\njobs: {}\n", ["pull_request", "push"]),
        ("on:\n  pull_request:\n  push:\n    branches: [main]\n  workflow_dispatch:\njobs: {}\n",
         ["pull_request", "push", "workflow_dispatch"]),
        ("'on':\n  schedule:\n    - cron: '0 3 * * 1'\njobs: {}\n", ["schedule"]),
        ("name: nothing\njobs: {}\n", []),
    ]
    for text, want in cases:
        got = fn(text)
        if list(got) != want:
            raise AssertionError(f"for\n{text}expected {want} (sorted), got {got}")


@_ref
def _job_commands(workflow_text: str, job: str) -> list:
    import yaml
    data = yaml.safe_load(workflow_text) or {}
    steps = ((data.get("jobs") or {}).get(job) or {}).get("steps") or []
    out = []
    for s in steps:
        run = s.get("run") if isinstance(s, dict) else None
        if run:
            out += [ln.strip() for ln in str(run).splitlines() if ln.strip()]
    return out


@exercise("w10.job_commands", hint="data['jobs'][job]['steps'] is a list of dicts. Keep the `run` ones, split "
                                   "multi-line `run: |` blocks into lines, strip them and drop empty lines.")
def _t_job_commands(fn):
    wf = """name: CI
on: push
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - name: Install
        run: python -m pip install -r requirements.txt
      - name: Test
        run: |
          python -m pytest -q

          python -m pytest --doctest-modules src
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
"""
    cases = [("test", ["python -m pip install -r requirements.txt", "python -m pytest -q",
                       "python -m pytest --doctest-modules src"]),
             ("build", []), ("missing", [])]
    for job, want in cases:
        got = fn(wf, job)
        if list(got) != want:
            raise AssertionError(f"for job {job!r} expected {want}, got {got}")


@_ref
def _matrix_versions(workflow_text: str, job: str) -> list:
    import yaml
    data = yaml.safe_load(workflow_text) or {}
    j = (data.get("jobs") or {}).get(job) or {}
    versions = ((j.get("strategy") or {}).get("matrix") or {}).get("python-version", [])
    out = []
    for v in versions:
        if isinstance(v, float):
            raise ValueError(f"python-version {v} is a number: quote it")
        out.append(str(v))
    return out


@exercise("w10.matrix_versions",
          hint="Read jobs -> job -> strategy -> matrix -> python-version. A YAML number like 3.10 arrives as the "
               "float 3.1: raise ValueError when you see a float.")
def _t_matrix(fn):
    def wf(versions: str) -> str:
        return f"on: push\njobs:\n  t:\n    runs-on: ubuntu-latest\n    strategy:\n      matrix:\n" \
               f"        python-version: {versions}\n    steps: []\n"
    good = [(wf('["3.11", "3.12", "3.13"]'), ["3.11", "3.12", "3.13"]), (wf("['3.10']"), ["3.10"])]
    for text, want in good:
        got = fn(text, "t")
        if list(got) != want:
            raise AssertionError(f"expected {want}, got {got}")
    if list(fn("on: push\njobs:\n  t:\n    runs-on: x\n    steps: []\n", "t")) != []:
        raise AssertionError("a job with no matrix should give []")
    for bad in ["[3.10, 3.11]", "[3.12]"]:
        try:
            fn(wf(bad), "t")
        except ValueError:
            continue
        raise AssertionError(f"python-version: {bad} contains unquoted numbers (3.10 becomes 3.1!): raise "
                             "ValueError")


def _steps(job: dict) -> list:
    return [s for s in (job.get("steps") or []) if isinstance(s, dict)]


def _uses_index(steps, action):
    return next((k for k, s in enumerate(steps) if str(s.get("uses", "")).split("@")[0] == action), None)


def _run_index(steps, pattern):
    return next((k for k, s in enumerate(steps) if re.search(pattern, str(s.get("run", "")))), None)


def _workflow_problems(text: str, matrix: bool = False, docker: bool = False, hardened: bool = False) -> list[str]:
    data = _yaml(text)
    if not isinstance(data, dict):
        return ["the workflow should be a YAML mapping with keys like name, on and jobs"]
    trig = _triggers(text)
    problems = []
    if "push" not in trig or "pull_request" not in trig:
        problems.append(f"the workflow runs on {trig or 'nothing'}: it should run on push AND pull_request")
    jobs = data.get("jobs") or {}
    if not isinstance(jobs, dict) or not jobs:
        return problems + ["there are no jobs"]
    test_job = None
    for name, job in jobs.items():
        if isinstance(job, dict) and _run_index(_steps(job), r"pytest") is not None:
            test_job = (name, job)
            break
    if test_job is None:
        return problems + ["no job runs pytest"]
    name, job = test_job
    steps = _steps(job)
    if not str(job.get("runs-on", "")).startswith("ubuntu"):
        problems.append(f"job {name!r} should run on a GitHub-hosted Linux runner (runs-on: ubuntu-latest)")
    co, sp = _uses_index(steps, "actions/checkout"), _uses_index(steps, "actions/setup-python")
    inst, test = _run_index(steps, r"pip install"), _run_index(steps, r"pytest")
    if co is None:
        problems.append("the job never checks out your code (uses: actions/checkout@v7)")
    if sp is None:
        problems.append("the job never sets up Python (uses: actions/setup-python@v7)")
    if inst is None:
        problems.append("the job never installs the dependencies (pip install -r requirements.txt)")
    elif not re.search(r"-r\s+\S*requirements", str(steps[inst].get("run", ""))):
        problems.append("install from your requirements file(s) with pip install -r, so CI tests what you pinned")
    if None not in (co, sp, inst, test) and not (co < sp < inst < test):
        problems.append("the steps are in the wrong order: checkout, set up Python, install, then test")
    for k in (co, sp):
        if k is not None and not re.search(r"@v\d+", str(steps[k].get("uses"))):
            problems.append(f"pin the action version ({steps[k].get('uses')} should end in @v and a number)")
    if sp is not None:
        ver = (steps[sp].get("with") or {}).get("python-version")
        if ver is None:
            problems.append("setup-python needs `with: python-version: ...`")
        elif isinstance(ver, float):
            problems.append(f"python-version {ver} is read as a number: put it in quotes")
        if matrix:
            if "matrix.python-version" not in str(ver):
                problems.append("setup-python should use ${{ matrix.python-version }}")
            if (steps[sp].get("with") or {}).get("cache") != "pip":
                problems.append("turn on pip caching in setup-python (cache: pip)")
    if matrix:
        mv = ((job.get("strategy") or {}).get("matrix") or {}).get("python-version")
        if not isinstance(mv, list):
            problems.append("add strategy: matrix: python-version: [...] to the test job")
        elif any(isinstance(v, float) for v in mv):
            problems.append("the matrix has unquoted versions: quote every one (\"3.11\")")
        elif {str(v) for v in mv} != {"3.11", "3.12", "3.13"}:
            problems.append("the matrix should test exactly 3.11, 3.12 and 3.13")
        if (job.get("strategy") or {}).get("fail-fast") is not False:
            problems.append("set fail-fast: false so one failing version does not cancel the others")
    if hardened:
        perms = data.get("permissions")
        if not (isinstance(perms, dict) and perms.get("contents") == "read" and
                all(v in ("read", "none") for v in perms.values())):
            problems.append("give the workflow read-only permissions at the top: permissions: contents: read")
        for jn, j in jobs.items():
            t = j.get("timeout-minutes") if isinstance(j, dict) else None
            if not isinstance(t, int) or not 1 <= t <= 60:
                problems.append(f"job {jn!r} needs timeout-minutes between 1 and 60")
                break
    if _unsafe_secret_steps(text):
        problems.append("a run step puts ${{ secrets.* }} straight into a command; pass secrets through env:")
    if docker:
        djob = next(((n, j) for n, j in jobs.items() if isinstance(j, dict) and
                     _run_index(_steps(j), r"docker build") is not None), None)
        if djob is None:
            problems.append("add a job that builds the image (run: docker build ...)")
        else:
            dn, dj = djob
            needs = dj.get("needs")
            needs = [needs] if isinstance(needs, str) else (needs or [])
            if dn != name and name not in needs:
                problems.append(f"the docker job should wait for the tests: needs: {name}")
            if _uses_index(_steps(dj), "actions/checkout") is None:
                problems.append("the docker job also needs actions/checkout (each job starts on a fresh machine)")
            if not re.search(r"docker build\s+(-t|--tag)\s+\S+", str(_steps(dj)[_run_index(_steps(dj), r"docker build")].get("run"))):
                problems.append("tag the image you build: docker build -t NAME:TAG .")
    return problems


def _first(problems):
    if problems:
        more = f" (and {len(problems) - 1} more)" if len(problems) > 1 else ""
        raise AssertionError(problems[0] + more)


@exercise("w10.workflow", hint="Start from the anatomy picture in section 2: on, jobs, runs-on, then four steps.")
def _t_workflow(answer):
    _first(_workflow_problems(_text(answer, "workflow")))


@exercise("w10.workflow_matrix", hint="Add strategy (fail-fast and matrix) to the job, and use the matrix value and "
                                      "cache: pip in setup-python.")
def _t_workflow_matrix(answer):
    _first(_workflow_problems(_text(answer, "workflow"), matrix=True))


@_ref
def _first_failures(log: str) -> list:
    out = []
    for line in log.splitlines():
        line = re.sub(r"^\d{4}-\d\d-\d\dT[\d:.]+Z\s+", "", line.strip())
        m = re.match(r"^(FAILED|ERROR)\s+(\S+)", line)
        if m and m.group(2) not in out:
            out.append(m.group(2))
    return out


@exercise("w10.failures", hint="Look for lines that START with FAILED or ERROR (after an optional GitHub timestamp) "
                              "and take the next word: the test id. Keep the order, no duplicates.")
def _t_failures(fn):
    log1 = """============================= test session starts ==============================
collected 5 items

tests/test_api.py ..F.F                                                  [100%]

=================================== FAILURES ===================================
___________________________ test_predict_rejects_negative ___________________________
    def test_predict_rejects_negative():
>       assert r.status_code == 422
E       assert 200 == 422
FAILED tests/test_api.py::test_predict_rejects_negative - assert 200 == 422
FAILED tests/test_api.py::test_score_in_range - AssertionError: 1.7
========================= 2 failed, 3 passed in 0.41s =========================="""
    log2 = "\n".join(f"2026-11-26T10:0{k}:00.1234567Z {line}" for k, line in enumerate([
        "collected 0 items / 1 error",
        "==================================== ERRORS ====================================",
        "ERROR tests/test_model.py - ModuleNotFoundError: No module named 'joblib'",
        "!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!"]))
    log3 = "tests/test_a.py ...  [100%]\n============ 3 passed in 0.02s ============"
    cases = [(log1, ["tests/test_api.py::test_predict_rejects_negative", "tests/test_api.py::test_score_in_range"]),
             (log2, ["tests/test_model.py"]), (log3, []),
             ("FAILED tests/t.py::test_x[3.12] - x\nFAILED tests/t.py::test_x[3.12] - x", ["tests/t.py::test_x[3.12]"])]
    for log, want in cases:
        got = fn(log)
        if list(got) != want:
            raise AssertionError(f"expected {want}, got {got} (first log lines: {log.splitlines()[0][:60]!r})")


@_ref
def _unsafe_secret_steps(workflow_text: str) -> list:
    import yaml
    data = yaml.safe_load(workflow_text) or {}
    out = []
    for jn, job in (data.get("jobs") or {}).items():
        for k, s in enumerate((job or {}).get("steps") or []):
            if isinstance(s, dict) and re.search(r"\$\{\{\s*secrets\.", str(s.get("run", ""))):
                out.append(s.get("name") or f"{jn} step {k + 1}")
    return out


@exercise("w10.unsafe_secrets", hint="For every job and every step, look only at the `run` text for '${{ secrets.' "
                                     "(spaces after '{{' are allowed). Use the step's name, or 'JOB step N' "
                                     "(counting from 1) when it has none.")
def _t_unsafe(fn):
    wf = """on: push
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - name: Safe
        env:
          TOKEN: ${{ secrets.DEPLOY_TOKEN }}
        run: ./deploy.sh
      - name: Leaky
        run: 'curl -H "Authorization: ${{secrets.DEPLOY_TOKEN}}" https://example.org'
      - run: echo ${{ secrets.OTHER }}
  test:
    runs-on: ubuntu-latest
    steps:
      - run: python -m pytest
"""
    got = fn(wf)
    if list(got) != ["Leaky", "deploy step 4"]:
        raise AssertionError(f"expected ['Leaky', 'deploy step 4'], got {got}. Passing a secret via env: is the "
                             "safe pattern and must not be reported.")
    if list(fn("on: push\njobs: {}\n")) != []:
        raise AssertionError("a workflow with no jobs should give []")


@exercise("w10.workflow_hardened", hint="Two keys: `permissions:` at the top level, and `timeout-minutes:` inside "
                                        "every job.")
def _t_hardened(answer):
    _first(_workflow_problems(_text(answer, "workflow"), hardened=True))


# =========================================================================== notebook 40: lab
LAB_RUNTIME = {"fastapi", "uvicorn", "scikit-learn", "joblib"}
LAB_DEV = {"pytest", "jupyter", "notebook", "matplotlib", "ipykernel", "jupyterlab", "black", "ruff", "httpx"}


@exercise("w10.lab_requirements", hint="Pin every line with ==. scikit-learn must be the version the model was "
                                       "trained with (sklearn.__version__). Test tools go in requirements-dev.txt.")
def _t_lab_requirements(answer):
    import sklearn
    reqs = _parse_requirements(_text(answer, "requirements.txt"))
    missing = LAB_RUNTIME - set(reqs)
    if missing:
        raise AssertionError(f"the service needs {sorted(missing)} at run time")
    loose = sorted(n for n, v in reqs.items() if v is None)
    if loose:
        raise AssertionError(f"{loose} are not pinned with ==: a rebuild next month could install different code")
    if reqs["scikit-learn"] != sklearn.__version__:
        raise AssertionError(f"scikit-learn is pinned to {reqs['scikit-learn']}, but the model was trained and saved "
                             "with a different version here: a pickled model should be loaded by the same version")
    dev = sorted(set(reqs) & LAB_DEV)
    if dev:
        raise AssertionError(f"{dev} are development tools: they make the image bigger and do not serve "
                             "predictions; put them in requirements-dev.txt")


_LAB_APP = '''
from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI()


class Basket(BaseModel):
    n_items: int = Field(ge=1, le=100)
    total: float = Field(ge=0)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/predict")
def predict(b: Basket):
    risk = 1 / (1 + 2.718281828 ** -(-2 + 0.08 * b.n_items + 0.004 * b.total))
    return {"return_risk": round(risk, 4), "model_version": "test"}
'''
_LAB_MUTANTS = {
    "health is broken": _LAB_APP.replace('return {"status": "ok"}', 'return {"status": "starting"}'),
    "health returns an error status": _LAB_APP.replace(
        'def health():\n    return {"status": "ok"}',
        'def health():\n    from fastapi import HTTPException\n    raise HTTPException(503, "not ready")'),
    "no input validation": _LAB_APP.replace("Field(ge=1, le=100)", "Field()").replace("Field(ge=0)", "Field()"),
    "score is not a probability": _LAB_APP.replace("round(risk, 4)", "round(-2 + 0.08 * b.n_items + 0.004 * b.total, 4)"),
    "response field renamed": _LAB_APP.replace('"return_risk"', '"risk"'),
}


def _run_student_tests(test_text: str, app_source: str) -> list[str]:
    """Run every test_* function of the student's file against `app_source`; return the names that failed."""
    pkg = types.ModuleType("app")
    pkg.__path__ = []
    main = types.ModuleType("app.main")
    exec(compile(app_source, "app/main.py", "exec"), main.__dict__)
    saved = {k: sys.modules.get(k) for k in ("app", "app.main")}
    sys.modules["app"], sys.modules["app.main"] = pkg, main
    pkg.main = main
    try:
        mod = types.ModuleType("student_tests")
        exec(compile(test_text, "tests/test_api.py", "exec"), mod.__dict__)
        tests = [(n, f) for n, f in vars(mod).items() if n.startswith("test_") and callable(f)]
        if not tests:
            raise AssertionError("your test file has no functions whose names start with test_")
        failed = []
        for n, f in tests:
            try:
                f()
            except TypeError as err:
                if "positional argument" in str(err):
                    raise AssertionError(f"{n} takes arguments: this lab's tests must be plain functions without "
                                         "fixtures")
                failed.append(n)
            except Exception:
                failed.append(n)
        return failed
    finally:
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v


@exercise("w10.lab_tests", hint="Write at least one test per promise of the API: /health says ok, a good basket "
                                "gets 200 with return_risk between 0 and 1, and bad baskets get 422.")
def _t_lab_tests(answer):
    text = _text(answer, "test file")
    if "TestClient" not in text:
        raise AssertionError("use fastapi.testclient.TestClient to call the app")
    failed = _run_student_tests(text, _LAB_APP)
    if failed:
        raise AssertionError(f"against a CORRECT app these tests fail: {failed}. A test must only fail when the "
                             "app breaks a promise (are you checking an exact score?)")
    for bug, src in _LAB_MUTANTS.items():
        if not _run_student_tests(text, src):
            raise AssertionError(f"your tests pass on an app with a planted bug ({bug}): add a test that catches it")


LINT_CODES = ["unpinned_base", "runs_as_root", "deps_after_code", "pip_cache", "secret_in_env", "shell_form_cmd"]


@_ref
def _lint_dockerfile(text: str) -> set:
    ins = _parse_dockerfile(text)
    codes = set()
    base = next((a.split()[0] for i, a in ins if i == "FROM"), "")
    if not _is_pinned(base):
        codes.add("unpinned_base")
    users = [a.strip() for i, a in ins if i == "USER"]
    if not users or users[-1] in ("root", "0"):
        codes.add("runs_as_root")
    pip = [k for k, (i, a) in enumerate(ins) if i == "RUN" and "pip install" in a]
    code_copy = [k for k, (i, a) in enumerate(ins) if i in ("COPY", "ADD") and "requirements" not in a]
    if pip and code_copy and min(code_copy) < min(pip):
        codes.add("deps_after_code")
    if any("--no-cache-dir" not in ins[k][1] for k in pip):
        codes.add("pip_cache")
    if _find_secrets(text):
        codes.add("secret_in_env")
    cmds = [a for i, a in ins if i == "CMD"]
    if cmds and _cmd_list(cmds[-1]) is None:
        codes.add("shell_form_cmd")
    return codes


_LINT_CASES = [
    (GOOD_38, set()),
    (GOOD_38.replace("python:3.12-slim", "python"), {"unpinned_base"}),
    (GOOD_38.replace("python:3.12-slim", "python:latest"), {"unpinned_base"}),
    (GOOD_38.replace("USER appuser\n", ""), {"runs_as_root"}),
    (GOOD_38.replace("USER appuser", "USER root"), {"runs_as_root"}),
    ("FROM python:3.12-slim\nWORKDIR /app\nCOPY . .\nRUN pip install -r requirements.txt\nCMD python app.py\n",
     {"runs_as_root", "deps_after_code", "pip_cache", "shell_form_cmd"}),
    (GOOD_38.replace("EXPOSE 8000", "ENV API_KEY=abc123\nEXPOSE 8000"), {"secret_in_env"}),
    (GOOD_38.replace("EXPOSE 8000", "ENV LOG_LEVEL=info\nEXPOSE 8000"), set()),
    (GOOD_38.replace("RUN pip install --no-cache-dir -r requirements.txt",
                     "RUN pip install --no-cache-dir -r requirements.txt\nRUN pip install uvicorn"), {"pip_cache"}),
    ("FROM python:3.12-slim\nRUN pip install --no-cache-dir flask\nUSER nobody\nCMD [\"python\", \"-m\", \"flask\"]\n",
     set()),
]


@exercise("w10.lab_lint", hint="Reuse parse_dockerfile, is_pinned and find_secrets (given above). Each rule looks at "
                               "only a few instruction types; a Dockerfile with no problems gives an empty set.")
def _t_lab_lint(fn):
    for text, want in _LINT_CASES:
        got = fn(text)
        if not isinstance(got, set):
            raise AssertionError(f"return a set of codes, got {type(got).__name__}")
        unknown = got - set(LINT_CODES)
        if unknown:
            raise AssertionError(f"unknown codes {sorted(unknown)}; use only {LINT_CODES}")
        if got != want:
            miss, extra = sorted(want - got), sorted(got - want)
            first = text.strip().splitlines()
            raise AssertionError(f"for a Dockerfile ({len(first)} lines, starting {first[0]!r}) "
                                 + (f"you missed {miss}" if miss else "")
                                 + (" and " if miss and extra else "")
                                 + (f"you wrongly reported {extra}" if extra else ""))


@exercise("w10.lab_dockerignore", hint="Same rules as notebook 38: anchored at the root, **/ for any depth. The lab "
                                       "also has a model/ folder and tests that the image does need or does not.")
def _t_lab_dockerignore(answer):
    yes = DOCKERIGNORE_YES + ["tests/test_api.py", ".github/workflows/ci.yml", "requirements-dev.txt"]
    no = ["app/main.py", "requirements.txt", "model/model.joblib", "model/metadata.json"]
    why = dict(DOCKERIGNORE_WHY, tests="tests run in CI, not inside the service image",
               **{".github": "the CI workflow is not part of the image", "requirements-dev": "dev tools stay out"})
    _check_ignore_file(_text(answer, ".dockerignore"), yes, no, why, False, ".dockerignore")


@exercise("w10.lab_dockerfile", hint="Notebook 38's Dockerfile, plus a COPY for model/ and a HEALTHCHECK that uses "
                                     "python (the slim image has no curl).")
def _t_lab_dockerfile(answer):
    _first(_dockerfile_problems(_text(answer, "Dockerfile"), need_healthcheck=True, need_model=True))


@exercise("w10.lab_workflow", hint="Two jobs: `test` (notebook 39) and `docker`, which needs test, checks out the "
                                   "code and runs docker build -t ... . Keep permissions and timeouts.")
def _t_lab_workflow(answer):
    _first(_workflow_problems(_text(answer, "workflow"), docker=True, hardened=True))


# =========================================================================== quizzes
register_quiz(
    "w10.37_q1", "c",
    "`which python` (or `where python` on Windows) shows which interpreter your terminal runs. If it is not inside "
    ".venv, the activation did not happen in this terminal, or VS Code uses a different interpreter.",
    {"a": "Reinstalling changes nothing if the terminal keeps running a different Python.",
     "b": "The package is installed, just into a different Python; installing it globally hides the real problem.",
     "d": "The error comes from Python looking in the wrong environment, not from the code."})
register_quiz(
    "w10.37_q2", "b",
    "requirements.txt records WHAT the project needs (and which versions), so anyone can rebuild .venv. The .venv "
    "folder itself is large, machine-specific and full of absolute paths.",
    {"a": "Committing .venv is exactly what to avoid: it does not work on another OS or another folder.",
     "c": "A venv belongs to one project, not to one user; each project gets its own.",
     "d": "Git can store it, but it is hundreds of MB of machine-specific files: rebuild it instead."})
register_quiz(
    "w10.37_q3", "a",
    "The debugger stops BEFORE running the line with the breakpoint, so you see the values as they are at that "
    "moment and can step forward one line at a time.",
    {"b": "Nothing is deleted; a breakpoint only pauses execution.",
     "c": "It pauses before the line runs, not after.",
     "d": "Breakpoints work in any Python file and in notebook cells (Debug Cell)."})
register_quiz(
    "w10.37_q4", "d",
    "PATH is searched in order and the first match wins. Activating a venv puts .venv/bin (or .venv\\Scripts) in "
    "FRONT of PATH, which is all activation really does.",
    {"a": "Activation does not copy anything; it changes the environment variables of this terminal.",
     "b": "No reinstall happens; the venv already contains its own python.",
     "c": "The system Python is untouched; it is just found later in PATH."})
register_quiz(
    "w10.37_q5", "b",
    "Pinned versions (==) make 'works on my machine' reproducible: CI, a colleague and the Docker image install "
    "the same code you tested.",
    {"a": "Pins do not make installs faster; they make them repeatable.",
     "c": "Pinning is about reproducibility, not licensing.",
     "d": "You still update, deliberately: change the pin, run the tests, commit."})

register_quiz(
    "w10.38_q1", "c",
    "Containers share the host's kernel and isolate processes and files, so they start in about a second and are "
    "tens to hundreds of MB. A VM boots a whole operating system.",
    {"a": "Containers are not faster at computing; they are lighter to start and ship.",
     "b": "A container does not include a kernel; a VM does.",
     "d": "Isolation is weaker than a VM's, not stronger: a container is not a security sandbox on its own."})
register_quiz(
    "w10.38_q2", "b",
    "Each instruction is a cached layer. Copying only requirements.txt first means the slow pip install layer is "
    "reused until the requirements change; code changes only re-run the cheap COPY.",
    {"a": "Order does not change what ends up in the image; it changes what can be reused from the cache.",
     "c": "Docker copies whatever you ask, in any order.",
     "d": "Image size is the same in both orders."})
register_quiz(
    "w10.38_q3", "d",
    "127.0.0.1 inside a container is the container's own loopback; requests forwarded by -p arrive on its network "
    "interface, so the server must listen on 0.0.0.0.",
    {"a": "The port mapping is fine; the server inside just refuses outside connections.",
     "b": "EXPOSE only documents a port; it does not publish it or change what the server listens on.",
     "c": "Docker does not block the port; the app inside is listening on the wrong address."})
register_quiz(
    "w10.38_q4", "a",
    "Anything in an image (ENV values, files, even files deleted in a later layer) can be read by anyone who has "
    "the image. Secrets are passed at run time (-e or a secrets manager).",
    {"b": "Layers are stored as they were built: a later RUN rm does not remove the file from the earlier layer.",
     "c": "Private registries limit who can pull, but everyone who can pull can read the secret.",
     "d": "ENV is visible in `docker inspect`, not encrypted."})
register_quiz(
    "w10.38_q5", "c",
    "A container's filesystem disappears with it (--rm, or a new image). Data you want to keep lives outside: a "
    "volume or bind mount (-v), a database, or object storage.",
    {"a": "Restarting does not help: a new container starts from the image again.",
     "b": "docker commit makes a new image; it is not how you keep data.",
     "d": "Writes inside the container work; they are just thrown away with it."})

register_quiz(
    "w10.39_q1", "b",
    "Each job runs on a fresh virtual machine: nothing from your laptop is there, so the workflow must check out "
    "the code, install Python and the dependencies, and only then run the tests.",
    {"a": "The runner is a clean machine; your local .venv does not exist there.",
     "c": "GitHub does not guess; the steps are exactly what the YAML lists.",
     "d": "Jobs do not share files unless you pass artifacts explicitly."})
register_quiz(
    "w10.39_q2", "c",
    "Unquoted, YAML reads 3.10 as the number 3.1, and setup-python installs Python 3.1, which fails or picks the "
    "wrong version. Quoting keeps it a string.",
    {"a": "Quotes are not about speed.",
     "b": "GitHub accepts both; it is YAML that changes the value.",
     "d": "3.12 survives as a number, but 3.10 does not; quote all of them for consistency."})
register_quiz(
    "w10.39_q3", "a",
    "Read the log from the first red step down to the first FAILED/ERROR line: it names the test and the "
    "assertion. Then reproduce it locally with the same command.",
    {"b": "Re-running hides real failures; only re-run when you have evidence of a flaky external problem.",
     "c": "Deleting or skipping a failing test removes the safety net it provides.",
     "d": "The last lines are usually the summary; the cause is the first failure above it."})
register_quiz(
    "w10.39_q4", "d",
    "CI (and branch protection that requires it) turns 'please run the tests' into a rule: nothing reaches main "
    "unless the tests passed on a clean machine.",
    {"a": "CI cannot prove code is correct; it proves the tests you wrote pass.",
     "b": "Tests still run locally while you work; CI is the shared, final check.",
     "c": "CI runs whatever you configure; it is not a code reviewer."})
register_quiz(
    "w10.39_q5", "b",
    "Secrets are injected as environment variables for the steps that need them; GitHub masks them in logs. "
    "Putting ${{ secrets.X }} into a command line risks printing it and shell-injection.",
    {"a": "Secrets must never be committed, not even in a private repository.",
     "c": "Workflows from forks do not receive secrets by default, which is a protection, not a way to share them.",
     "d": "Encoding (e.g. base64) is not encryption; anyone can decode it."})

register_quiz(
    "w10.40_q1", "c",
    "The service needs the same scikit-learn that saved the model; a different version may refuse to load it or, "
    "worse, load it and predict differently.",
    {"a": "Pinning is about the model file's compatibility, not speed.",
     "b": "pip happily installs any version; the risk is at load time.",
     "d": "Any version string works for pip; it must match the training environment."})
register_quiz(
    "w10.40_q2", "b",
    "A test should check the API's promises (status codes, fields, ranges), not one exact score: the score changes "
    "every time the model is retrained, and that is not a bug.",
    {"a": "An exact-score test breaks on every retrain and teaches the team to ignore red builds.",
     "c": "Contract tests do catch real bugs: the planted bugs in this lab are all contract breaks.",
     "d": "Testing only /health would miss broken predictions and missing validation."})
register_quiz(
    "w10.40_q3", "a",
    "The HEALTHCHECK runs inside the container; Docker (and orchestrators) mark the container unhealthy if "
    "/health stops answering, so it can be restarted or taken out of service.",
    {"b": "It does not change the server; it only probes it.",
     "c": "It runs inside the container, not from the CI runner.",
     "d": "Healthchecks are about running containers, not about building images."})
register_quiz(
    "w10.40_q4", "d",
    "`needs: test` makes the docker job wait for the test job and skip if it failed, so a broken commit never "
    "produces an image.",
    {"a": "Jobs without needs run in parallel, so the image could be built from failing code.",
     "b": "needs controls order and dependency, not the runner.",
     "c": "Both jobs still check out the code themselves; needs does not share files."})


# The notebook-38 helpers, ready-made for the lab (notebook 40), so the lab does not depend on finished lessons.
nb38_helpers = types.SimpleNamespace(parse_dockerfile=_parse_dockerfile, is_pinned=_is_pinned,
                                     find_secrets=_find_secrets)
