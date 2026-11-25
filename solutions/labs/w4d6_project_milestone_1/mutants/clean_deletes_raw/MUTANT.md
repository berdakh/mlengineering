# Mutant: clean deletes the raw data

`make clean` runs `rm -rf data`, which removes the downloaded raw files along with the derived
ones. Caught by `test_clean_removes_build_outputs`.
