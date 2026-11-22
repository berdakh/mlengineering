# Mutant: a timestamp in the provenance block

`provenance` records `datetime.now()`. It feels like good provenance, but it makes every rebuild
different, so nobody can confirm that a rebuild reproduced the numbers. Record the code version and
input hashes instead; when the run happened belongs in a log. Caught by
`test_deleted_intermediate_is_rebuilt_identically`.
