# Mutant: the format version is recorded but not checked

Bundles carry `format_version`, but `load_bundle` reads any version. A bundle written by a newer
release, with fields this code does not know or interprets differently, loads silently. Caught by
`test_newer_format_version_is_refused_with_both_versions`.
