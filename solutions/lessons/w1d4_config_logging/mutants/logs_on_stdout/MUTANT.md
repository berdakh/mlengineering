# Mutant: logs_on_stdout

Console logs go to stdout, where they are interleaved with the JSON result; `pumpwatch train ... | jq` breaks. Caught by `test_stdout_is_exactly_one_json_object`.

Changed file: `src/pumpwatch/logging_setup.py`
