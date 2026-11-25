# lock_without_hashes
Plausible mistake: `pip freeze > requirements.lock` (or pip-compile without --generate-hashes). Every version is pinned, but nothing guarantees the file pip downloads under that name is the one you tested. Expected to fail: test_every_package_has_a_sha256_hash.
