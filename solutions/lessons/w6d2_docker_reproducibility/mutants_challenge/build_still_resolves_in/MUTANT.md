# build_still_resolves_in
Plausible mistake: a correct lock that nothing uses: build.sh still installs requirements.in, so the build still picks 1.1.0. Expected to fail: test_build_script_installs_the_lock_with_hash_checking.
