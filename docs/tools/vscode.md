---
title: "VS Code"
parent: Tool guides
nav_order: 12
---

# VS Code
{: .no_toc }

Visual Studio Code ("VS Code") is a free code editor from Microsoft that runs on Windows, macOS and Linux. With
two extensions it becomes a complete Python workbench: editor, terminal, notebook runner, test runner and
debugger in one window. This guide is the reference for Week 10, where the course moves from Colab to your own
computer ([notebook 37](../notebooks/37_vscode_local_setup.html)).

1. TOC
{:toc}

## What it is, and why teams use it

Colab is a notebook in a browser on someone else's computer. Real projects are **folders of files** (packages,
tests, configuration, a Dockerfile) that live in Git and run on many machines. An editor that understands the
whole folder catches mistakes as you type, jumps to the definition of any function, runs one test with a click,
and pauses a running program so you can look inside. VS Code is the most widely used editor for this, and
remote-development features let the same window work on a server or inside a container later in your career.

## Installing it, with Python and Git

Install three things, then check each one in a **new** terminal (a terminal reads its settings when it starts).

| | Windows | macOS | Linux (Ubuntu/Debian) |
|---|---|---|---|
| Python 3.12 | python.org installer; tick **Add python.exe to PATH** | python.org installer | usually installed; add `sudo apt install python3-venv` |
| Git | git-scm.com installer (defaults are fine) | `xcode-select --install` | `sudo apt install git` |
| VS Code | code.visualstudio.com | code.visualstudio.com; drag to Applications | code.visualstudio.com (`.deb`), or the Snap store |
| Check | `python --version`, `git --version`, `code --version` | `python3 --version`, `git --version`, `code --version` | same as macOS |

On macOS, if `code` is not found, open VS Code, press `Cmd+Shift+P`, and run **Shell Command: Install 'code'
command in PATH**.

Then add two extensions: open the Extensions panel (`Ctrl+Shift+X`, macOS `Cmd+Shift+X`), search and install
**Python** (by Microsoft; it brings Pylance, the code-intelligence engine, and the debugger) and **Jupyter** (by
Microsoft). Useful later: **Docker** (by Microsoft) and **GitHub Actions** (by GitHub), which help with Week 10's
files.

**Keyboard shortcuts in this guide** use Windows/Linux keys; on macOS replace `Ctrl` with `Cmd` (except
`` Ctrl+` ``, which is the same on every system).

## The window

| Area | Where | What for |
|---|---|---|
| Explorer | left bar, top icon | the files of the open folder |
| Search | left bar | search (and replace) across all files |
| Source Control | left bar | Git: changed files, staging, commits |
| Run and Debug | left bar | start the debugger |
| Testing | left bar, beaker icon | discover and run tests |
| Editor | centre | files and notebooks, in tabs |
| Panel | bottom (`` Ctrl+` ``) | terminal, problems, debug console |
| Status bar | bottom edge | the selected Python interpreter, Git branch, errors |

The **Command Palette** (`Ctrl+Shift+P`) runs any command by name. When you do not know where something is, type
what you want there.

## Open a folder, not a file

Always use **File → Open Folder** (or `code .` in a terminal inside the folder). VS Code then treats the folder as
the **workspace**: searches, the terminal, test discovery and settings all refer to it. Opening single files
works, but nothing knows about your project.

The typical first session with a project:

```bash
git clone https://github.com/berdakh/mlengineering.git
cd mlengineering
python -m venv .venv                     # macOS/Linux: python3 -m venv .venv
source .venv/bin/activate                # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
code .
```

## Virtual environments and the interpreter

A **virtual environment** is a folder (by convention `.venv` in the project) with its own Python launcher and
its own installed packages, so each project has the versions it needs. VS Code must know which Python to use:

1. `Ctrl+Shift+P` → **Python: Select Interpreter**;
2. pick the entry whose path contains `.venv` (VS Code usually offers it first, marked *Recommended*);
3. check the status bar: it shows the version and `('.venv': venv)`.

From then on, **new** terminals in VS Code activate `.venv` automatically (the prompt shows `(.venv)`), the editor
resolves imports against its packages, and notebooks and tests use it.

| Task | macOS / Linux | Windows PowerShell |
|---|---|---|
| Create | `python3 -m venv .venv` | `python -m venv .venv` |
| Activate | `source .venv/bin/activate` | `.venv\Scripts\Activate.ps1` |
| Which Python runs? | `which python` | `where python` (first line wins) |
| Install | `python -m pip install -r requirements.txt` | same |
| Leave | `deactivate` | `deactivate` |

Always install with `python -m pip`: it installs into the Python you will run, whatever the PATH says.

## The integrated terminal

`` Ctrl+` `` opens a terminal at the workspace folder. The `+` button opens more; the drop-down next to it picks the
shell (on Windows choose PowerShell or *Git Bash*). Everything from [the terminal guide](terminal.html) works
here. Two tips: `Ctrl+C` stops a running program (such as a server), and a terminal opened *before* you selected
the interpreter is not activated; close it and open a new one.

## Notebooks in VS Code

Open any `.ipynb` file. Click **Select Kernel** (top right) → **Python Environments** → `.venv`. The first time,
VS Code asks to install `ipykernel` (the bridge between Jupyter and a Python environment): accept. Run a cell with
`Shift+Enter`; **Run All** is in the toolbar. The **Variables** button shows every variable in a table.

This course's notebooks run unchanged: their first cell detects that it is not in Colab and finds the course
folder. Files you write go to `work/` inside the course folder instead of `/content/work`.

## Running tests

Tell VS Code to use pytest once: **Testing** panel → **Configure Python Tests** → **pytest** → the folder with the
tests. It writes this to `.vscode/settings.json`:

```json
{
    "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests"]
}
```

(On Windows the interpreter path is `${workspaceFolder}\\.venv\\Scripts\\python.exe`.) The Testing panel then
lists every test; the green triangles run one test, a file or all of them, and failures show inline next to the
failing line. A terminal command does the same: `python -m pytest -q`.

Committing `.vscode/settings.json` shares these settings with the team. It is JSON: double quotes only, `true`
and `false` without quotes, commas between entries and none after the last. (VS Code tolerates comments in this
file; other tools reading it may not.)

## The debugger

Instead of adding `print` calls, pause the program and look:

1. click in the margin left of a line number: a red dot, a **breakpoint**;
2. start debugging: `F5` for the current file (choose *Python File*), **Debug Test** (right-click the test's
   triangle) for a test, or **Debug Cell** in a notebook's cell menu;
3. execution stops **before** the breakpoint line runs. The left side shows **Variables** (every local and
   global), **Watch** (expressions you add) and **Call Stack** (how you got here);
4. step: `F10` runs the line (*step over*), `F11` enters the function called on this line (*step into*),
   `Shift+F11` finishes the current function (*step out*), `F5` continues to the next breakpoint;
5. the **Debug Console** evaluates any expression at the paused moment, for example `len(values)` or
   `df.head()`.

Right-click a breakpoint → **Edit Breakpoint** to make it conditional (`n_items > 50`): it only stops when the
condition is true, which is how you catch the one bad row in ten thousand.

## Git in VS Code

The **Source Control** panel shows changed files. Click `+` to stage a file (same as `git add`), type a message,
and press **Commit**; **Sync** pushes and pulls. Clicking a changed file shows a side-by-side diff, which is the
easiest way to review your own change before committing. The terminal commands from
[Git and GitHub](git-github.html) still work and are what you will use in scripts and CI.

## Files every project has

```
project/
├── .venv/                  # the virtual environment (never committed)
├── .vscode/settings.json   # shared editor settings (committed)
├── .gitignore              # what Git ignores (committed)
├── requirements.txt        # pinned runtime dependencies (committed)
├── requirements-dev.txt    # -r requirements.txt + test tools (committed)
├── src/ or app/            # the code
└── tests/                  # pytest tests
```

A good `.gitignore` for a Python project starts with:

```
.venv/
__pycache__/
.ipynb_checkpoints/
.pytest_cache/
.env
```

`.env` (a file of secrets) is ignored; a committed `.env.example` with fake values documents what is needed.

## Common errors and how to read them

| You see | It means | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'x'` | this interpreter lacks `x` | check the status bar interpreter; activate `.venv`; `python -m pip install x` |
| Import underlined in yellow, but the code runs | Pylance uses a different interpreter | **Python: Select Interpreter** → `.venv` |
| `'python' is not recognized ...` (Windows) / `command not found: python` | no Python on PATH | reinstall with *Add to PATH*, or use `py` (Windows) / `python3`; reopen the terminal |
| `... Activate.ps1 cannot be loaded because running scripts is disabled` | PowerShell's execution policy | once: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| `error: externally-managed-environment` | pip refuses to change the system Python | use a venv |
| Notebook: *Select a kernel* keeps appearing / `ipykernel` required | the notebook has no environment yet | Select Kernel → `.venv`; accept installing `ipykernel` |
| Testing panel empty, or *pytest discovery error* | wrong test folder or an import error in a test file | open **Output → Python** for the message; run `python -m pytest` in the terminal to see it plainly |
| Terminal does not show `(.venv)` | it was opened before the interpreter was selected | open a new terminal |

When a fix does not work, answer one question first: **which Python is running?** (`which python` / `where
python`, `sys.executable`, the status bar.) Most setup problems end there.

## Cheat sheet

| Action | Shortcut / command |
|---|---|
| Command Palette | `Ctrl+Shift+P` |
| Open a file by name | `Ctrl+P` |
| Terminal | `` Ctrl+` `` |
| Select interpreter | Palette → *Python: Select Interpreter* |
| Run cell / run and advance | `Ctrl+Enter` / `Shift+Enter` |
| Go to definition / back | `F12` / `Alt+Left` (macOS `Ctrl+-`) |
| Rename a symbol everywhere | `F2` |
| Find in all files | `Ctrl+Shift+F` |
| Comment a line | `Ctrl+/` |
| Format the file | `Shift+Alt+F` (macOS `Shift+Option+F`) |
| Debug: start/continue, step over, into, out | `F5`, `F10`, `F11`, `Shift+F11` |
| Toggle breakpoint | `F9` |
| Open folder from the terminal | `code .` |

## Where next

- Official docs: [Python in VS Code](https://code.visualstudio.com/docs/python/python-tutorial),
  [Jupyter notebooks in VS Code](https://code.visualstudio.com/docs/datascience/jupyter-notebooks),
  [Debugging](https://code.visualstudio.com/docs/python/debugging) and
  [Testing](https://code.visualstudio.com/docs/python/testing).
- In this course: [notebook 37](../notebooks/37_vscode_local_setup.html), the [terminal](terminal.html),
  [Git and GitHub](git-github.html), [pytest](pytest.html) and [Python packaging](packaging.html) guides, then
  [Docker](docker.html).
