---
title: "Git and GitHub"
parent: Tool guides
nav_order: 4
---

# Git and GitHub

**Git** records the history of a project: every saved version, who made it, and why. **GitHub** hosts Git
repositories online so a team can share them, review changes and run automatic checks. Every software team uses
both (or close relatives such as GitLab). This guide covers the ideas, the commands you will use every week,
setting Git up on your own computer, pushing to GitHub safely, and what to do when something goes wrong.

## Why version control

Without it, projects collect files like `train_final_v3_fixed.py`, nobody can say which code produced last month's
model, and a bad edit cannot be undone. With Git:

- every **commit** is a named, dated snapshot you can return to;
- `git diff` shows exactly what changed between any two versions;
- **branches** let you try an idea without touching the working version;
- several people can change the same project and **merge** their work;
- with GitHub, every change can be **reviewed** before it reaches the main line.

For ML work this also means reproducibility: a model or a result can be traced back to the exact code (commit) that
produced it.

## The ideas in one picture

```
working folder  --git add-->  staging area  --git commit-->  local repository  --git push-->  remote (GitHub)
      ^                                                            |                              |
      +---------------------- git restore / git switch ------------+          <---git pull--------+
```

- **Repository (repo):** a project folder whose history Git tracks. The history lives in a hidden `.git` folder.
- **Working folder:** the files you see and edit.
- **Staging area:** the changes you have chosen (with `git add`) for the next commit. It lets you commit some edits
  and not others.
- **Commit:** a snapshot of all tracked files, with a message, an author, a time, and a link to its parent commit.
  Each commit has an ID (a *hash*) such as `9050dd5`.
- **Branch:** a movable label pointing at a commit; `main` is the usual name of the trusted line.
- **HEAD:** "where you are now", normally the latest commit of the current branch.
- **Remote:** a copy of the repository elsewhere, usually on GitHub, by convention named `origin`.

## Installing and configuring Git

| Where | How |
|---|---|
| **Colab** | already installed: run commands with `!git ...` (each `!` line is a fresh shell: `!cd repo && git status`) |
| **Linux** | `sudo apt install git` (Debian/Ubuntu) or your distribution's package manager |
| **macOS** | run `git --version` in Terminal; if missing, macOS offers to install the Command Line Tools |
| **Windows** | install Git for Windows from [git-scm.com](https://git-scm.com/download/win); use **Git Bash** as your terminal |

Then tell Git who you are, once per computer (the name and email appear in every commit):

```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
git config --global init.defaultBranch main
```

On GitHub you can use the private *noreply* email shown in *Settings → Emails* if you do not want your address public.
For a single practice repository, leave out `--global` to set these only there (that is what the course notebooks do).

## The 20% you will use 80% of the time

### Start or get a repository

```bash
git init -b main                 # turn the current folder into a repo, with branch "main"
git clone https://github.com/berdakh/mlengineering.git   # download a repo (sets up "origin")
```

### The everyday loop

```bash
git status                       # what changed? what is staged? (run it constantly)
git diff                         # line-by-line changes not yet staged
git add train.py README.md       # stage specific files
git add .                        # stage everything in this folder (check git status first!)
git diff --staged                # what will go into the commit
git commit -m "Add baseline training script"
git log --oneline                # history, one line per commit
git log --oneline --graph --all  # with branches drawn
```

**Good commit messages** say what the change does, in the imperative, in about 50 characters: *Add CSV validator*,
*Fix off-by-one in row numbers*, *Ignore the data folder*. Not *update*, *stuff* or *asdf*. Commit small, related
changes together, and often.

### What not to commit: `.gitignore`

A file named `.gitignore` in the repository lists patterns Git should ignore:

```
data/
outputs/
*.log
.env
__pycache__/
.venv/
.ipynb_checkpoints/
```

Commit the `.gitignore` itself. Keep out of Git: datasets (large; store them elsewhere), generated files (models,
reports, caches: they can be recreated), virtual environments, and above all **secrets** (passwords, API keys,
tokens, `.env` files). Anything committed stays in history even if you delete it later, and once pushed to a public
repository, assume it has been copied. If a secret is ever committed, **revoke it** (create a new key) first; cleaning
history comes second.

`git check-ignore -v path` tells you which rule ignores a file.

### Branches and merging

```bash
git branch                       # list branches (* = current)
git switch -c feature-x          # create a branch and move to it
# ... edit, add, commit ...
git switch main                  # back to main (files change to main's version)
git merge feature-x              # bring feature-x's commits into main
git branch -d feature-x          # delete the branch label after merging
```

If `main` has not moved since the branch started, the merge is a **fast-forward**: `main` simply moves to the
branch's last commit. If both moved, Git creates a **merge commit** with two parents.

Older tutorials use `git checkout` for both switching branches and restoring files; `git switch` and `git restore`
are the newer, clearer commands that do one job each.

### Undoing things

| Situation | Command |
|---|---|
| Discard uncommitted edits to a file (back to the last commit) | `git restore file` |
| Unstage a file (keep the edits) | `git restore --staged file` |
| Fix the message of the last commit (not yet pushed) | `git commit --amend -m "Better message"` |
| Undo a commit that is already shared | `git revert <commit-id>` (adds a new commit that reverses it) |
| See an old version of a file | `git show <commit-id>:path/to/file` |

`git restore` throws away uncommitted work in that file, and `git reset --hard` throws away all of it: use them
deliberately. Rewriting commits that others already have (with `--amend`, `reset` or `rebase` after pushing) causes
trouble for them; prefer `git revert` on shared branches.

### Merge conflicts

If two branches changed the same lines, `git merge` stops and marks the file:

```
<<<<<<< HEAD
threshold = 0.5
=======
threshold = 0.7
>>>>>>> feature-x
```

The part above `=======` is your current branch; below is the branch being merged. Edit the file to the version you
want (delete the markers), then `git add file` and `git commit`. `git merge --abort` returns to before the merge.
Conflicts are normal, not failures; small, frequent merges keep them small.

## GitHub

### Remotes, push and pull

```bash
git remote -v                    # list remotes
git remote add origin https://github.com/<you>/<repo>.git
git push -u origin main          # upload main and remember origin/main as its upstream
git push                         # later pushes
git pull                         # download and merge others' commits
```

Run `git pull` before starting work, and push when a piece of work is done.

### Creating a repository and pushing (on your own computer)

1. Sign in at [github.com](https://github.com/), click **New** (or **+ → New repository**), choose a name, Public or
   Private, and *do not* add a README if you already have one locally. Click **Create repository**.
2. GitHub shows the commands for "push an existing repository". In your project folder:

   ```bash
   git remote add origin https://github.com/<you>/<repo>.git
   git push -u origin main
   ```

3. **Authentication.** GitHub does not accept your account password for `git push`. Choose one:
   - **GitHub CLI** (simplest): install `gh` from [cli.github.com](https://cli.github.com/), run `gh auth login`, and
     follow the prompts; Git then uses it.
   - **Git Credential Manager**, included in Git for Windows and available for macOS and Linux: the first push opens
     a browser window to sign in.
   - **SSH keys**: see GitHub's documentation *Connecting to GitHub with SSH*.

   Never paste a password or token into a notebook, a script or a commit. This is why the course never pushes from
   Colab.

### Pull requests

A **pull request (PR)** asks for a branch to be reviewed and merged on GitHub:

1. `git switch -c fix-row-numbers`, commit, then `git push -u origin fix-row-numbers`.
2. GitHub shows a banner **Compare & pull request**. Click it, write a title and a description (what and why, how
   you tested it), and click **Create pull request**.
3. The PR page has tabs: **Conversation** (description, comments, approvals), **Commits**, **Checks** (automated
   tests from CI, week 10), and **Files changed** (a diff where reviewers click a line to comment).
4. Push more commits to the same branch to address comments; the PR updates itself.
5. When approved and checks are green, click **Merge pull request**. Then locally: `git switch main && git pull`.

To contribute to someone else's project you first **fork** it (your own copy on GitHub), push a branch to your fork,
and open a PR from there.

Other GitHub features you will meet: **Issues** (tasks and bug reports), the README rendered on the repository's
front page, **Actions** (CI, week 10), and **Releases**.

## Git in Colab and in notebooks

- In Colab you can practise every local command with `!git`; the runtime and the repository disappear when it resets.
- Notebooks are JSON files that include outputs, so diffs of `.ipynb` files are noisy. Commit notebooks with
  meaningful outputs, keep reusable code in `.py` files, and do not commit large outputs (images, long tables)
  without reason.

## Common errors and how to read them

| Message | Meaning | Fix |
|---|---|---|
| `fatal: not a git repository` | you are not inside a repo | `cd` into it, or `git init` |
| `Author identity unknown ... Please tell me who you are` | name/email not configured | the two `git config` commands above |
| `nothing to commit, working tree clean` | no changes since the last commit | not an error |
| `nothing added to commit but untracked files present` | you forgot `git add` | `git add file` |
| `error: pathspec 'x' did not match any file(s)` | misspelled file or branch name | `git status`, `git branch` |
| `Your local changes ... would be overwritten by checkout/merge` | uncommitted edits would be lost | commit them, or `git stash`, then retry |
| `CONFLICT (content): Merge conflict in file` | both sides changed the same lines | edit, `git add`, `git commit` (see above) |
| `! [rejected] main -> main (fetch first)` | the remote has commits you do not have | `git pull`, resolve if needed, push again |
| `remote: Support for password authentication was removed` | used a password to push | use `gh auth login` or a credential manager |
| `fatal: refusing to merge unrelated histories` | the remote was created with its own first commit | create remotes empty, or ask for help before forcing |
| `detached HEAD` | you checked out a commit, not a branch | `git switch main` (or `git switch -c new-branch` to keep work) |

## Cheat sheet

| Task | Command |
|---|---|
| One-time setup | `git config --global user.name "..."`, `user.email "..."`, `init.defaultBranch main` |
| New repo / copy a repo | `git init -b main` / `git clone URL` |
| Where am I | `git status`, `git branch`, `git log --oneline --graph --all` |
| What changed | `git diff`, `git diff --staged` |
| Save a version | `git add files` then `git commit -m "Message"` |
| Ignore files | add patterns to `.gitignore`, commit it |
| Branch / switch / merge | `git switch -c b`, `git switch main`, `git merge b` |
| Undo edits to a file | `git restore file` |
| Unstage | `git restore --staged file` |
| Reverse a shared commit | `git revert <id>` |
| Share | `git push -u origin main`, then `git push`; `git pull` |
| Review | push a branch, open a pull request on GitHub |

## Where next

- [Pro Git](https://git-scm.com/book/en/v2), the free official book: chapters 1-3 cover everything here.
- [GitHub Skills](https://skills.github.com/): short interactive courses, including your first pull request.
- [Oh Shit, Git!?!](https://ohshitgit.com/): fixes for common mistakes in plain language.
- In this course: [The terminal](terminal.html); week 10 adds GitHub Actions.
