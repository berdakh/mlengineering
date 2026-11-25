# Mutant: put_always_201

PUT answers 201 Created every time, so a client cannot tell 'created' from 'already there' and
may wrongly assume a fresh burn-in started.
