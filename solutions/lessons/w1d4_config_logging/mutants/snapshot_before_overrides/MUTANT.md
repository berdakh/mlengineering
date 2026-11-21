# Mutant: snapshot_before_overrides

`config.json` is written from the file-only configuration, while training uses the configuration with overrides applied. The run directory then documents a run that did not happen. Caught by `test_command_line_beats_file_and_is_in_the_snapshot`.

Changed file: `src/pumpwatch/cli.py`
