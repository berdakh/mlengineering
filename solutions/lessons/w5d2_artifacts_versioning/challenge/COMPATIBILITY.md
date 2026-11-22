# Compatibility policy: flowguard-logistic bundles (reference solution)

**What is stored.** The decision function itself: 16 coefficients and an intercept (`weights.npz`,
float64, written with `numpy.savez`), and in `model.json` everything that defines how features are
built: burn-in length, calibration rule, clip, sensor order and the feature layout by name. The
scikit-learn object is *not* stored. Loading needs NumPy only.

**Why not pickle or joblib.** A pickle is a program: loading an untrusted one executes code. A pickled
scikit-learn estimator is also only guaranteed to load in the same scikit-learn version that wrote it;
scikit-learn warns about version mismatches and does not promise compatibility. This model's state is
17 numbers, so the cost of storing the mathematics is a 30-line loader, and the benefit is an artifact
that is safe to load and independent of library upgrades. For a model whose state is a large tree
ensemble, the trade would change: skops (a restricted, inspectable format for scikit-learn objects) or
ONNX would be the candidates, with the training library version pinned.

**What the loader refuses** (`BundleCompatibilityError` or `BundleIntegrityError`, both `ValueError`):
* any file whose SHA-256 differs from `checksums.json`, a missing file, or an unlisted file;
* a `format` other than `flowguard-bundle` or a `format_version` other than 1;
* a `kind` other than `logistic-z`;
* a sensor list or feature layout different from the one the loader implements (a different order would
  silently pair coefficients with the wrong features);
* weights with the wrong shapes.

**What is recorded but not enforced.** The training scikit-learn version and `C` (provenance), the
Python/NumPy/scikit-learn versions at save time (card). They do not affect loading because no
scikit-learn code runs at load time.

**Versioning.** Bundle *format* changes bump `format_version` (old loaders refuse new bundles). Model
*versions* follow MAJOR.MINOR.PATCH: PATCH for a re-save with identical scores (e.g. card text), MINOR
for retraining on new data with the same features and contract, MAJOR for a change in features, input
contract or score meaning (consumers' thresholds must be revisited). A registered version is never
overwritten.
