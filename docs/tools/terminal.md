---
title: "The terminal (bash)"
parent: Tool guides
nav_order: 3
---

# The terminal (bash)

The terminal is a text window where you type commands instead of clicking. ML engineers use it every day: to run
scripts and tests, use Git, inspect logs and data files, install packages, and work on remote servers and containers
that have no graphical interface at all. This guide covers opening one on any system, the commands you will use most,
how to combine them, and how to read the errors.

## What the terminal is

A few words that are often mixed up:

- The **terminal** is the window (on macOS: *Terminal*; on Windows: *Windows Terminal*; in VS Code: the *Terminal*
  panel).
- The **shell** is the program inside it that reads your commands and runs them. The most common is **bash**; macOS
  uses **zsh** by default, which accepts the same commands for everything in this guide. Windows has **PowerShell**,
  which is different; see below.
- A **command line** is one command you type: `ls -l data`.

Every command has the shape `program -options arguments`: `ls` is the program, `-l` an option (changes how it
behaves; long form `--long-option`), `data` an argument (what to work on). Options can be combined: `ls -l -a` is the
same as `ls -la`.

Why bother when you can click? Commands are **precise** (a command says exactly what happened), **repeatable** (copy it
into a script or documentation), **composable** (small tools combine into new ones), and **available everywhere**,
including servers, Docker containers and CI machines, which have no windows to click.

## Opening a terminal

| Where | How |
|---|---|
| **Colab** | prefix a line in a code cell with `!` (e.g. `!ls`). Each `!` line runs in a fresh shell, so `!cd x` does not stick: use `!cd x && ls`. (Colab Pro also has a *Terminal* button.) |
| **Linux** | open the *Terminal* app (often Ctrl+Alt+T). The shell is bash. |
| **macOS** | *Applications → Utilities → Terminal* (or Spotlight: type "Terminal"). The shell is zsh. |
| **Windows** | install **Git for Windows** ([git-scm.com](https://git-scm.com/download/win)), which includes **Git Bash**, a bash terminal; use it for this course. For a full Linux environment, install **WSL** (`wsl --install` in PowerShell as administrator). |
| **VS Code** | *View → Terminal* (Ctrl+\`). On Windows choose *Git Bash* in the terminal's drop-down. |

You type after the **prompt**, which often ends in `$` (or `%` in zsh): `student@laptop:~/projects$`. In
documentation, a leading `$` means "type the rest of this line"; do not type the `$`.

## Files and folders: the essentials

The shell always has a **working directory**, the folder commands act on by default.

| Command | What it does | Example |
|---|---|---|
| `pwd` | print the working directory | `pwd` → `/home/student/projects` |
| `ls` | list files | `ls`, `ls -l` (details), `ls -a` (include hidden files starting with `.`), `ls -lh` (human sizes) |
| `cd` | change directory | `cd data`, `cd ..` (up one), `cd ~` (home), `cd -` (back to previous) |
| `mkdir` | make a folder | `mkdir -p results/2024/march` (`-p`: create parents, no error if exists) |
| `touch` | create an empty file (or update its time) | `touch notes.txt` |
| `cp` | copy | `cp a.csv backup.csv`, `cp -r folder copy_of_folder` |
| `mv` | move or rename | `mv old.txt new.txt`, `mv file.txt archive/` |
| `rm` | delete | `rm file.txt`, `rm -r folder` |

**Paths.** An **absolute** path starts at the root `/` (`/home/student/data.csv`; on Windows in Git Bash, `C:\` is
`/c/`). A **relative** path starts at the working directory (`data/raw.csv`). Special names: `.` (this folder), `..`
(parent folder), `~` (your home folder).

**Spaces in names** must be quoted: `cd "My Documents"`. Easier: avoid spaces in file names you create.

**`rm` is permanent.** There is no recycle bin. Check with `ls` before `rm -r`, and never run `rm -rf` on a path you
have not read twice.

**Tab completion.** Type the first letters of a file or folder and press **Tab**; the shell completes it. Press Tab
twice to list the options. This saves typing and prevents typos. **Up arrow** recalls previous commands; `history`
lists them; **Ctrl+C** stops a running command; **Ctrl+L** (or `clear`) clears the screen.

## Looking inside files

| Command | Shows | Example |
|---|---|---|
| `cat` | the whole file | `cat README.md` |
| `head` | the first lines (10 by default) | `head -n 5 data.csv` |
| `tail` | the last lines | `tail -n 20 server.log`; `tail -f server.log` follows new lines as they arrive (Ctrl+C to stop) |
| `less` | a scrollable view (local terminal) | `less big.log`: arrows to scroll, `/word` to search, `q` to quit |
| `wc` | counts | `wc -l data.csv` (lines), `wc -w` (words) |
| `grep` | lines that match a pattern | `grep ERROR server.log`; `-i` ignore case, `-c` count, `-v` invert, `-n` line numbers, `-r` search folders |
| `find` | files by name | `find . -name "*.csv"` |
| `du -sh` | size of a folder | `du -sh data/` |

`head` and `wc -l` are the first two commands to run on any data file: what does it look like, and how big is it?

## Combining commands: pipes and redirection

Programs read **standard input** and write **standard output** (and error messages to **standard error**). The shell
can connect them:

| Symbol | Meaning | Example |
|---|---|---|
| `a \| b` | pipe: output of `a` becomes input of `b` | `grep ERROR app.log \| wc -l` |
| `> file` | write output to a file (replaces it) | `grep ERROR app.log > errors.txt` |
| `>> file` | append output to a file | `echo "run finished" >> log.txt` |
| `2> file` | write *error* output to a file | `python train.py 2> errors.txt` |
| `a && b` | run `b` only if `a` succeeded | `cd project && python main.py` |
| `a ; b` | run `b` after `a` either way | `make; echo done` |

Tools that shine in pipes:

```bash
cut -d "," -f 2 data.csv          # column 2 of a comma-separated file
sort                              # sort lines; -n numeric, -r reverse, -u unique
uniq -c                           # count adjacent repeated lines (sort first!)
head -n 1                         # keep the first line
tr "A-Z" "a-z"                    # translate characters (here: to lower case)
```

The classic "what is most common?" pipeline:

```bash
cut -d " " -f 4 server.log | sort | uniq -c | sort -rn | head -n 5
```

Build such a pipeline one stage at a time, looking at the output after each `|`.

## Running programs

```bash
python script.py data.csv         # run a Python script with an argument
python -m pytest -q               # run a module as a program (week 8)
pip install -r requirements.txt   # install packages listed in a file
which python                      # which program will run when you type "python"
echo $?                           # exit code of the last command: 0 = success
```

The **exit code** is how a program reports success (0) or failure (anything else). `&&`, scripts, schedulers and CI
systems (week 10) all rely on it.

**Environment variables** are named settings visible to programs: `echo $HOME`, `export MODE=test`. Secrets such as
API keys are often passed this way, so never print them in shared notebooks or logs.

**`PATH`** is the list of folders the shell searches for programs. *command not found* usually means a program is not
installed or its folder is not on `PATH`.

## Getting help

- `ls --help` prints a summary of options for most commands.
- `man ls` opens the full manual on Linux and macOS (`q` to quit). Not available in Git Bash; use `--help`.
- [explainshell.com](https://explainshell.com/) explains each part of a command line you paste in.

## PowerShell and Windows notes

If you open plain *PowerShell* or *Command Prompt* instead of Git Bash, some commands differ: `dir` instead of `ls`
(PowerShell also accepts `ls`), `type` instead of `cat`, `findstr` instead of `grep`, `\` instead of `/` in paths, and
`.venv\Scripts\activate` instead of `source .venv/bin/activate`. This course writes bash; Git Bash or WSL lets you
follow it exactly.

## Common errors and how to read them

| Message | Meaning | Fix |
|---|---|---|
| `command not found` (or `is not recognized` on Windows) | the program is not installed, or misspelled, or not on `PATH` | check spelling; install it; on Windows use Git Bash |
| `No such file or directory` | the path does not exist from where you are | `pwd` and `ls`; check spelling and case (`Data` ≠ `data` on Linux) |
| `Permission denied` | you may not read/write/run that file | do not reach for `sudo` blindly; work in your own folders |
| `Is a directory` | a file command got a folder | add `-r` (for `cp`/`rm`) or pick a file inside |
| `Not a directory` | `cd` into a file | `ls` to see what it is |
| nothing happens, no prompt | the command is waiting for input (e.g. `cat` with no file) or still running | Ctrl+C |
| `>` and a strange prompt | you opened a quote and did not close it | Ctrl+C and retype |
| `rm: cannot remove 'x': Directory not empty` | `rm` without `-r` on a folder | `rm -r x`, after checking its contents |

In Colab, a failing `!` command prints its error but does not stop the notebook; read the output.

## Cheat sheet

| Task | Command |
|---|---|
| Where am I / what is here | `pwd`, `ls -la` |
| Move around | `cd folder`, `cd ..`, `cd ~` |
| Make / copy / move / delete | `mkdir -p a/b`, `cp -r src dst`, `mv old new`, `rm -r folder` |
| Peek at a file | `head -n 5 f`, `tail -n 5 f`, `wc -l f`, `less f` |
| Search | `grep -n "text" f`, `grep -r "text" folder`, `find . -name "*.py"` |
| Most common values | `cut -d "," -f 2 f \| sort \| uniq -c \| sort -rn \| head` |
| Save output | `cmd > out.txt`, `cmd >> out.txt`, `cmd 2> err.txt` |
| Run if previous worked | `a && b` |
| Exit code | `echo $?` |
| Run Python | `python script.py args` |
| Help | `cmd --help`, `man cmd` |
| Stop / clear / history | Ctrl+C, Ctrl+L, Up arrow, `history` |
| In Colab | `!cmd`, and `!cd folder && cmd` |

## Where next

- [The Linux command line for beginners](https://ubuntu.com/tutorials/command-line-for-beginners) (Ubuntu tutorial).
- [The Missing Semester of Your CS Education](https://missing.csail.mit.edu/), lectures 1-2 (shell and shell tools).
- GNU bash manual: [gnu.org/software/bash/manual](https://www.gnu.org/software/bash/manual/).
- In this course: [Git and GitHub](git-github.html), which you will drive from this terminal.
