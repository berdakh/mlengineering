# Mutant: `--data` is parsed but ignored

The CLI accepts `--data` yet still reads `data/synthetic/pump_vibration.csv`
relative to the current working directory - a leftover from the script. Run from
the repository root with the default file it prints the right numbers, so a
"does it run?" test passes.

Rejected by: `test_cli_reproduces_the_script_from_another_directory`
(different cwd, differently named data file). Note that the missing-file check
still passes: a relative path that does not exist also produces a clean error.
