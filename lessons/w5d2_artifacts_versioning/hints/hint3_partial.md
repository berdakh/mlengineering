# Hint 3 (partial implementation)

```python
def verify_bundle(bundle_dir):
    bundle = Path(bundle_dir)
    path = bundle / CHECKSUMS
    if not path.is_file():
        raise BundleIntegrityError(f"{bundle}: no {CHECKSUMS}")
    listed = json.loads(path.read_text())["files"]
    present = {p.name for p in bundle.iterdir() if p.name != CHECKSUMS}
    extra = sorted(present - set(listed))
    if extra:
        raise BundleIntegrityError(f"{bundle}: unexpected file {extra[0]!r}")
    for name, digest in listed.items():
        ...  # missing file? digest mismatch? name the file in the message
    return listed
```

```python
def promote(root, name, version):
    home = Path(root) / name
    if version not in list_versions(root, name):
        raise RegistryError(...)
    verify_bundle(home / version)
    tmp = home / ".current.tmp"
    tmp.write_text(version + "\n")
    os.replace(tmp, home / "current")
```

Challenge: the decision function of a fitted binary `LogisticRegression` is
`X @ lr.coef_.ravel() + lr.intercept_[0]`. Save those numbers and everything that defines `X`.
