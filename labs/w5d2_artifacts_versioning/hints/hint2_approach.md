# Hint 2 (approach)

* `save_bundle`: check the card fields first and the directory second, so a refused call leaves nothing
  behind. Write `model.json`, `reference.npz`, `card.json`; compute their SHA-256; write
  `checksums.json` last. `sha256_file` and `_json_bytes` are given.
* `verify_bundle`: the set of files present (minus `checksums.json`) must equal the set listed; then
  compare each digest. Put the file name in every error message.
* `load_bundle`: verify, read `model.json`, check `format`, `format_version` and `kind`, strip those
  three keys and pass the rest to `Detector.from_config`.
* `register`: read name and version from the bundle; validate the version with the `SEMVER` regex;
  refuse an existing destination; copy into `tempfile.mkdtemp(dir=<root>/<name>)`, verify the copy,
  `os.replace` it onto the destination.
* `list_versions`: sort with a key that turns "1.10.0" into `(1, 10, 0)`.
* `promote`: check the version is registered and verifies; write `.current.tmp`; `os.replace` onto
  `current`.
