# lock_top_level_only
Plausible mistake: hashing and pinning only the five packages named in requirements.in. Their dependencies (starlette, pydantic-core, anyio, ...) are still resolved on build day; in hash-checking mode pip refuses the install outright. Expected to fail: test_the_lock_contains_the_full_runtime_closure.
