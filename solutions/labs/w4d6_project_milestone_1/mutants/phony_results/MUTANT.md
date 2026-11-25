# Mutant: every target is phony

Declaring the file targets .PHONY makes `make evaluate` rerun everything every time, so make never
reports 'up to date' and a five-minute evaluation runs on every call. Caught by
`test_up_to_date_after_build`.
