# Hint 1 (concept)

The audit has one job: run your project the way a stranger would, with nothing but the commit. Every
function in the tool removes one way the author's machine could help:

* `clone` removes untracked files (so never copy the working directory);
* `make_venv` removes installed packages (so system site packages stay off);
* `read_requirements` removes "whatever version pip picks today" (so only `==` is accepted);
* `scan_absolute_paths` removes paths that only exist on one machine;
* `compare_headline` removes "close enough" (so the tolerance is absolute and stated).

A finding is useful only if it names the cause. A crash in the clone is a symptom: read the step's output to
say *which* module or file was missing.
