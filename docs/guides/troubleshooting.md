---
title: Troubleshooting
parent: Guides
nav_order: 5
---

# Troubleshooting
{: .no_toc }

Start with the error message: the last line usually names the problem, and the lines above it show where.
Each tool guide also has a "common errors" section ([SQL](../tools/sql.html), [pandas](../tools/pandas.html),
[pytest](../tools/pytest.html), [Docker](../tools/docker.html) ...).

1. TOC
{:toc}

---

## Colab and notebooks

**`NameError: name 'grade' is not defined` (or `sql`, `pd`, ...).** The setup cell, or a cell above, has not run in
this session. Run the notebook from the top: *Runtime → Run before* in Colab.

**A cell worked an hour ago and now fails.** Colab disconnected and reset the runtime. Run the setup cell again,
then the cells above the one you are on.

**`FileNotFoundError` for a course file.** The setup cell moves into the course folder; something later changed
the working directory (`%cd`, `os.chdir`). Re-run the setup cell.

**My answers disappeared.** A Colab runtime is deleted when it disconnects. Use *File → Save a copy in Drive*
before you stop, and open your copy next time.

**The setup cell fails while cloning or installing.** Usually a network hiccup: *Runtime → Restart session* and run
it again. If `/content/mlengineering` exists but is incomplete, delete it first: `!rm -rf /content/mlengineering`.

## Grading

**⏳ not attempted yet.** The exercise still contains the starter (`# YOUR CODE HERE`, `raise NotImplementedError`,
or `"?"` in a quiz). Replace it with your answer.

**❌ with a message.** The grader ran your code on several inputs and one behaved differently from what the task
asks. Read the message and the hint, test your code on the case it describes, fix, re-run.

**❌ your code raised an error.** Your function crashed on one of the grader's inputs, often an edge case such as
an empty table, a missing value or a tie. Try that case yourself in a new cell.

**It passes in my head but not in the grader.** Re-run the cell that *defines* your function or query before the
grader cell; the grader sees the last version you ran.

## SQL

**`no such table` / `no such column`.** Check names with `tables()` and `schema("orders")`. Text values need single
quotes: `WHERE city = 'Almaty'`.

**The numbers are too big after a JOIN.** Fan-out: joining one row to many repeats it. Compare row counts before
and after each join (notebook 07).

**Zero rows and no error.** Often `= NULL` (use `IS NULL`) or a text value with different capitalisation.

## Your own computer (Weeks 10-11)

**`python: command not found` or the wrong version.** On macOS and Linux try `python3`; on Windows, the `py`
launcher. You need 3.11 or newer: `python3 --version`.

**`ModuleNotFoundError` in VS Code although you installed it.** VS Code is using a different interpreter. Choose
*Python: Select Interpreter* → `.venv`, and pick the same kernel for notebooks. See the
[VS Code guide](../tools/vscode.html).

**`source .venv/bin/activate` does nothing on Windows.** Use `.venv\Scripts\Activate.ps1` in PowerShell. If scripts
are blocked, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once.

**`docker: Cannot connect to the Docker daemon`.** Docker is not running: start Docker Desktop, or on Linux
`sudo systemctl start docker` and add yourself to the `docker` group (log out and in).

**`Address already in use`.** A server from earlier is still running on that port. Stop it (Ctrl+C in its terminal)
or use another port.

## GitHub

**`git push` asks for a password and rejects yours.** GitHub needs a personal access token or SSH key instead of
your password; see the [Git and GitHub guide](../tools/git-github.html).

**CI jobs fail within a second, with no logs.** The account has no Actions minutes left (private repositories
have a monthly quota; public ones are free). Check *Settings → Billing*.

## Advanced track

These came up while the advanced track was built and run; session numbers refer to
[its notebooks](../advanced/notebooks/).

* **`ModuleNotFoundError: No module named 'tomllib'`.** Python is 3.10 or older; use 3.11+.
* **The lab checks fail on a fresh starter.** Intended: they test work not yet done.
* **Two check folders in one `pytest` command clash on `conftest`.** Run them one at a time (`python wb.py check`
  already does).
* **Tiny differences in the last digits after a CSV round trip.** pandas' default float parser is not exact; read
  with `float_precision="round_trip"` (advanced 25).
* **Something that took seconds takes minutes.** NumPy/scikit-learn thread oversubscription on a busy machine. Set
  `OMP_NUM_THREADS=1` for the run.
* **Metrics differ on another machine.** Use the frozen split manifest (`v2.json`, 7 test experiments) and the
  versions in `requirements-lock.txt`.
* **A NaN in a request returns 500 instead of 422.** FastAPI's default validation handler tries to echo the input
  as JSON; the advanced service installs its own handler (advanced 28).
* **Latency jumps by about 40 ms with two or more uvicorn workers.** Nagle's algorithm; advanced 34 measures it and
  shows the `TCP_NODELAY` fix.
* **The container ignores Ctrl+C or takes 10 s to stop.** A shell-form `CMD` makes the shell PID 1, which does not
  forward SIGTERM. Use the exec form (advanced 31).
