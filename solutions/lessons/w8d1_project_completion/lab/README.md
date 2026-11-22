# w8d1 lab files

* `audit/clean_clone_check.py`: the audit tool. Seven functions raise `NotImplementedError`; the module
  docstring describes the whole procedure and `REPRODUCE.example.toml` the input format.
* `REPRODUCE.example.toml`: copy to your project root as `REPRODUCE.toml`.
* `DELIVERABLES.md`: fill in for your project.

Grade with `python wb.py check w8d1`. Then run the tool on your own repository:

```bash
python lessons/w8d1_project_completion/lab/audit/clean_clone_check.py ~/projects/flowguard \
    --log ~/projects/flowguard/audit/REPRODUCTION_LOG.md
```

Finding codes the checks rely on: `absolute_path`, `unpinned_requirement`, `missing_requirements_file`,
`install_failed`, `missing_dependency`, `missing_file`, `step_failed`, `headline_missing`,
`headline_mismatch`, `nondeterministic`, `clone_failed`, `missing_spec`.
