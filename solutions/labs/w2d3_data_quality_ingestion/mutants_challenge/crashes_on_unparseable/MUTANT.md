# Mutant: crashes_on_unparseable

`amount` is converted with `astype(float)`. The first non-numeric value raises `ValueError` and no
report is produced at all.

Why it is plausible: on the happy path it is identical, and the exception does "fail loudly". Why it is
wrong: a checker that crashes on the defects it exists to describe reports one problem (as a traceback,
without row identifiers) and hides the rest. Failing loudly is the *pipeline's* job, decided from a
complete report.

Rejected by: `test_row_level_violation...[amount_decimal_comma]`, `test_garbage_never_raises`.
