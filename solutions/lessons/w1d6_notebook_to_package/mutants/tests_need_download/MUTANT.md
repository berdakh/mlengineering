# Mutant: tests_need_download

One test reads `data/raw/skab` relative to the current directory. It passes on the author's machine
when pytest is started from the right folder after the download, and fails in CI, in a fresh clone,
and from any other directory. Tests of loading logic should build their own tiny inputs.

Rejected by `test_project_tests_pass_from_another_directory`.
