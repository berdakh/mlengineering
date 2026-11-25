# Mutant: stdout_noise

A friendly progress line is printed to stdout before the JSON. A human does not notice; `flowguard
summary ... | jq` and every script that parses the output break. Diagnostics belong on stderr (or in
logging, as in w1d4); stdout is the command's data channel.

Rejected by `test_summary_command`.
