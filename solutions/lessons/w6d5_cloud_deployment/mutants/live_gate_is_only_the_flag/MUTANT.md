# Mutant: live_gate_is_only_the_flag

Treats `--live` as sufficient authorisation and never reads SIGNOFF.md. The flag is typed in a
second (and lives on in shell history); the sign-off records a decision about cost and credentials made
after reading the briefing. A gate that can be satisfied without reading anything is not a gate.
