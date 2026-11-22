# Hint 1 (concept)

An artifact is trusted on load only if three questions have answers the loader checks:

1. **Are these the bytes that were saved?** A checksum per file, recorded when saving, recomputed when
   loading. Also: nothing missing, nothing extra.
2. **Can this code interpret them?** A format name and a format version written by the saver and
   compared by the loader *before* it interprets anything else.
3. **Does loading execute anything?** With JSON and numeric `.npz` it cannot, provided
   `numpy.load(..., allow_pickle=False)`.

A registry adds one rule: a version, once registered, is never changed. "Which model is live?" is a
separate, small, replaceable fact: the `current` pointer. Rolling back is promoting an older version.
