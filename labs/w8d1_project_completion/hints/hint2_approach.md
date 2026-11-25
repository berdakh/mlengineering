# Hint 2 (approach)

* `clone`: `subprocess.run(["git", "clone", "--quiet", source, str(dest)])`; then `git checkout ref` if the ref
  is not `HEAD`. Return a `clone_failed` finding on a non-zero exit.
* `scan_absolute_paths`: iterate over `tracked_files(repo)` (it already calls `git ls-files`), read text files,
  search each line with `ABS_PATH`, report `path.relative_to(repo)` and the 1-based line number.
* `read_requirements`: skip blank lines and comments; every other line must `PIN.match`; collect problems.
* `make_venv`: `venv.EnvBuilder(system_site_packages=False, with_pip=bool(requirements)).create(where)`; install
  with the venv's own `python -m pip install -r`.
* `run_steps`: `subprocess.run(step["run"], cwd=repo, env=step_env(bindir), capture_output=True, text=True,
  timeout=...)`; time it with `time.perf_counter()`; stop at the first non-zero exit and pass the combined output
  to `classify_failure`.
* `classify_failure`: two regular expressions, one for `ModuleNotFoundError: No module named '...'` and one for
  `FileNotFoundError` / `No such file or directory`.
* `compare_headline`: `get_path` both dictionaries; for numbers compare `abs(got - exp) <= tol`, otherwise `==`.
