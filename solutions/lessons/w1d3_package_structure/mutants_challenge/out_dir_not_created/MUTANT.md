# Mutant: `--out` only works if the directory already exists

`save_features` calls `to_csv` without creating parent directories. Tested by
hand with `--out features.csv` in the current directory it works; pointed at
`artifacts/v1/features.csv` it fails. (It even fails cleanly, with exit code 2 -
a tidy error message does not make the behaviour correct.)

Rejected by: the `feature_file` fixture (nested output path).
