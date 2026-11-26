---
title: "Google Colab"
parent: Tool guides
nav_order: 1
---

# Google Colab

Google Colab is the workbench for this course: a Jupyter notebook that runs on a Google computer and opens in your
browser. This guide explains what it is, how to open and save the course notebooks, the features you will use every
day, the errors beginners meet most often, and how to run the same notebooks on your own computer.

## What Colab is, and why we use it

A **notebook** is a document made of **cells**. A *text cell* holds explanations (written in Markdown, a simple
formatting language). A *code cell* holds Python; when you run it, its output (printed text, a table, a plot)
appears right below it. Notebooks are how data scientists and ML engineers explore data, try ideas and explain
results, because code, output and explanation sit side by side.

**Jupyter** is the open-source software behind notebooks. **Colab** is Google's hosted version of it:

- nothing to install: a browser and a Google account are enough, on Linux, macOS, Windows or a Chromebook;
- the code runs on a Google machine (a **runtime**, sometimes called the *kernel* or *backend*), not on your laptop;
- common libraries (NumPy, pandas, scikit-learn, matplotlib) are pre-installed, and you can install more with `pip`;
- free, with limits: a runtime is deleted after some idle time or after several hours of use.

That last point is the one to remember. **The runtime is temporary.** Its memory (your variables) and its disk
(any file you create) disappear when it is reset. Your notebook text and code are saved separately, in Google Drive,
once you have saved a copy there.

In industry you will also meet Jupyter in VS Code, JupyterLab on a team server, and managed notebooks on cloud
platforms (Databricks, SageMaker, Vertex AI). They work the same way: cells, a kernel, run order.

## Opening a course notebook

1. Open the course website's week page and click a notebook's **Colab** link, or click the **Open in Colab** badge
   at the top of a notebook. The URL looks like
   `https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/01_welcome_and_colab.ipynb`.
2. Sign in with a Google account if asked.
3. Run the first code cell, the **setup cell**. In Colab it downloads the course repository to
   `/content/mlengineering` (about 30 seconds) and installs the packages in `requirements.txt` (about a minute, once
   per runtime). It prints `Ready. Course folder: /content/mlengineering`.
4. Colab may warn *"This notebook was not authored by Google"*. Click **Run anyway**: the notebook comes from the
   course repository on GitHub.

## Saving your work

A notebook opened from GitHub is a read-only view. If you edit it and close the tab, your edits are gone.

**Save a copy in Drive** (menu *File → Save a copy in Drive*) creates your own copy in Google Drive, in a folder
called *Colab Notebooks*. From then on, Colab saves it automatically every few seconds, and you can reopen it from
[drive.google.com](https://drive.google.com) or from Colab's *File → Open notebook*. Do this at the start of every
notebook.

What survives what:

| | Closing the tab | Runtime reset (idle, *Disconnect and delete runtime*) |
|---|---|---|
| Notebook text and code (saved copy in Drive) | kept | kept |
| Cell outputs | kept in the saved notebook | kept in the saved notebook, but stale |
| Variables in memory | lost after the runtime stops | lost |
| Files you wrote to `/content` or `/tmp` | lost after the runtime stops | lost |
| The course folder `/content/mlengineering` | re-created by the setup cell | re-created by the setup cell |

To keep a *file* (a report, a model) across sessions, either download it (Files panel, right-click → Download) or
write it to your Google Drive after mounting it:

```python
from google.colab import drive
drive.mount("/content/drive")          # asks you to allow access, once per runtime
# now /content/drive/MyDrive is your Drive
```

Only mount Drive when you need it, and never write passwords or API keys into a notebook.

## The 20% of Colab you will use 80% of the time

### Running cells

| Action | How |
|---|---|
| Run the current cell, move to the next | **Shift+Enter** |
| Run the current cell, stay | **Ctrl+Enter** (macOS: **Cmd+Enter**) |
| Run everything from the top | *Runtime → Run all* |
| Restart and run everything | *Runtime → Restart session and run all* |
| Stop a cell that runs too long | the square stop button, or *Runtime → Interrupt execution* |
| New code / text cell | **+ Code** / **+ Text** at the top |

The number in brackets left of a code cell, such as `[7]`, is the order in which cells ran. A spinning circle means
it is still running; `[*]` in Jupyter means the same.

### The run-order trap

Cells run in the order *you* run them, not the order on the page. If you change cell 3 and do not re-run it, cell 5
still uses the old value. If you delete a cell, the variable it defined still exists in memory. A notebook that
works for you can therefore fail for someone else (or for you tomorrow).

The fix is a habit: before trusting a result, use **Runtime → Restart session and run all**. If everything still
works from a clean start, the notebook is honest.

### Shell commands with `!`

A line starting with `!` runs in the runtime's Linux shell instead of Python:

```python
!pwd                      # which folder am I in?
!ls data/course           # list files
!pip install -q pyyaml    # install a package (-q: quiet)
```

Each `!` line runs in a new shell, so `!cd folder` does not stick; write `!cd folder && ls` on one line. The
[terminal guide](terminal.html) covers the commands.

### Magic commands with `%`

Lines starting with `%` are IPython *magics*:

```python
%%writefile hello.py
print("hello")
```

When `%%writefile hello.py` is the first line of a cell, running the cell saves the rest of the cell as the file
`hello.py` instead of running it; `!python hello.py` then runs it.

```python
%time sum(range(10**6))   # how long one line takes
%who                      # list your variables
```

`%%writefile` is how the course creates small Python files and tests from inside a notebook.

### The Files panel

The folder icon on the left shows the runtime's disk. `/content` is the starting folder; the course is in
`/content/mlengineering`. You can upload a file from your computer (upload icon) and download one (right-click).
Remember that files here vanish with the runtime.

### Help while you type

- **Tab** completes names: type `pd.read_` and press Tab.
- Hover over a function, or run `help(len)` or `len?`, to see its documentation.
- In Colab, **Ctrl+/** (Cmd+/) comments out the selected lines.

### Runtime type

*Runtime → Change runtime type* lets you choose a GPU. This course never needs one; keep the default CPU, which
also keeps you within the free limits longer.

## Grading and progress in this course

Every graded exercise is followed by a grader cell, for example `grade("w01.add", add)`. It runs hidden tests and
prints ✅ when they pass, or ❌ with an explanation and a hint. Quizzes use `quiz("w01.01_q1", answer)` with the
letter you choose. You can re-run graders as often as you like; nothing is sent anywhere.

`from mlcourse.progress import mark` and `mark("01", "reading")` record your progress in a small file in the course
folder. In Colab that file disappears with the runtime unless you copy it to Drive; the notebooks' own outputs are
the record that matters.

## Common errors and how to read them

Python errors end with a **traceback**: the chain of calls that led to the error. Read it **from the bottom up**: the
last line names the error type and message, and the lines just above show where in *your* code it happened.

| You see | It usually means | Fix |
|---|---|---|
| `NameError: name 'x' is not defined` | the cell that defines `x` has not run in this runtime (or the runtime was reset) | run the cells above, or *Run all* |
| `ModuleNotFoundError: No module named 'mlcourse'` | the setup cell has not run in this runtime | run the setup cell |
| `NotImplementedError` | you ran an exercise cell without replacing `raise NotImplementedError()` | write your solution in place of that line |
| `FileNotFoundError` | wrong path, or the file was created in a runtime that has since been reset | check with `!ls`; re-run the cell that creates the file |
| `IndentationError` | inconsistent spaces at the start of lines | use 4 spaces per level; Colab's Tab key inserts them |
| *Runtime disconnected* | idle too long, or the session limit was reached | *Reconnect*, then run the setup cell and the cells you need |
| A cell runs forever (`[*]` or spinner) | an infinite loop or a very slow step | stop it; check loop conditions |
| `Your session crashed after using all available RAM` | data too large for memory | use a smaller sample; delete large variables |

Grader messages such as *"❌ w01.add: add(2, 3) should be 5, got -1"* (followed by a *Hint:* line) are not Python errors: they mean your code ran but did
something different from what was asked. Re-read the task and the hint.

## Running the notebooks on your own computer

Colab is enough for weeks 1-9. From week 10 you will also use VS Code locally. To run notebooks locally:

1. Install Python 3.10 or newer from [python.org](https://www.python.org/downloads/) (Windows: tick *Add Python to
   PATH*), and Git (see the [Git guide](git-github.html)).
2. In a terminal:

   ```bash
   git clone https://github.com/berdakh/mlengineering.git
   cd mlengineering
   python -m venv .venv
   source .venv/bin/activate          # Windows: .venv\Scripts\activate
   pip install -r requirements.txt jupyterlab
   jupyter lab
   ```

3. JupyterLab opens in your browser; open `notebooks/01_welcome_and_colab.ipynb`. The same setup cell detects that
   it is not in Colab and simply finds the course folder.

VS Code can also open `.ipynb` files directly once its Python and Jupyter extensions are installed.

## Cheat sheet

| Task | Do |
|---|---|
| Open a course notebook | week page → Colab link, or the badge |
| Keep your edits | *File → Save a copy in Drive* (once per notebook) |
| Run cell / run and stay | Shift+Enter / Ctrl+Enter |
| Clean re-run | *Runtime → Restart session and run all* |
| Stop a cell | stop button / *Runtime → Interrupt execution* |
| Shell command | `!ls`, `!pwd`, `!cd folder && command` |
| Install a package | `!pip install -q name` |
| Write a file from a cell | `%%writefile name.py` as the first line |
| Time a line | `%time expression` |
| Documentation | `help(fn)`, `fn?`, hover, Tab to complete |
| Keep a file | download it, or `drive.mount("/content/drive")` and save under `/content/drive/MyDrive` |
| After a reset | run the setup cell, then the cells you need |
| Read an error | bottom line first: type and message; then the lines above it |

## Where next

- Colab's own introduction: [colab.research.google.com](https://colab.research.google.com/) (the welcome notebook)
  and the FAQ at [research.google.com/colaboratory/faq.html](https://research.google.com/colaboratory/faq.html).
- Jupyter documentation: [docs.jupyter.org](https://docs.jupyter.org/).
- IPython magics: [ipython.readthedocs.io](https://ipython.readthedocs.io/en/stable/interactive/magics.html).
- In this course: [The terminal](terminal.html), [Python for engineers](python-for-engineers.html).
