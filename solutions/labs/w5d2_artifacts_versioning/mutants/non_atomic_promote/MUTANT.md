# Mutant: the pointer is rewritten in place

`promote` opens `current` and writes the new version into it. A service reading the pointer at that
moment can see an empty or truncated file and fail to resolve any model. Caught by
`test_promote_moves_the_pointer_atomically`.
