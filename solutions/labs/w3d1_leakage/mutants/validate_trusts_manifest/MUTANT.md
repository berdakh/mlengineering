# Mutant: validate_trusts_manifest

`validate_splits` only checks the `overlap_groups` listed in the manifest and never recomputes them from the data. A v1 manifest, which has no such key, passes although it separates experiments that share rows.
