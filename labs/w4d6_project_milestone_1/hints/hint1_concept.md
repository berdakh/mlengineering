# Hint 1: concept

* A Makefile rule is a promise: "this output depends on exactly these inputs". List an input you do
  not use and you get needless rebuilds; omit one you do use and you get stale outputs.
* `evaluate` is the only place numbers are born. If `render` needs a number that is not in the dict,
  the fix is in `evaluate`.
* Byte-identical rebuilds need three things: seeded randomness, deterministic ordering (sort keys and
  lists), and no reading of the clock or the host.
* `provenance` answers "could someone else rebuild this exact file?": input hashes, code version,
  library versions.
