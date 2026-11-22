"""Bundle the supervised logistic candidate (w4d5) without pickle, in the flowguard bundle layout.

Write this module. Contract (the checks rely on it):

``save_logistic(model, bundle_dir, metadata, *, version, name="flowguard-logistic") -> Path``
    ``model`` is a fitted ``flowguard.detectors.SupervisedLogistic`` (its ``model_`` attribute is a
    scikit-learn ``LogisticRegression`` trained on the 16 features [z_1..z_8, |z_1|..|z_8|]).
    Writes a bundle directory that ``flowguard.artifacts.verify_bundle`` and ``register`` accept:
    ``model.json`` (with ``format`` "flowguard-bundle", ``format_version`` 1, ``kind`` "logistic-z",
    ``name``, ``version``, the feature layout as a top-level list of the 16 feature names, and whatever
    else defines the function), ``card.json`` with the
    ``REQUIRED_CARD_FIELDS`` from ``metadata``, ``checksums.json`` covering every other file, and any
    arrays you need. No pickle, no joblib.

``load_logistic(bundle_dir) -> object with score_run(run) -> numpy array``
    ``score_run`` returns one score per row after the run's first ``n_burn`` rows (rows in time order),
    equal within 1e-12 to ``model.calibrate(run.iloc[:n_burn]).score(run.iloc[n_burn:])``.
    Verifies the checksums first. Refuses with a ``ValueError`` (the bundle errors in
    ``flowguard.artifacts`` are ``ValueError`` subclasses) a bundle whose format, format version or
    kind it does not read, and a feature layout it does not implement (the message must mention
    "feature").

Before you start: copy your finished lab module to ``src/flowguard/artifacts.py``.
Justify your serialisation choice and compatibility rules in COMPATIBILITY.md.
"""
from __future__ import annotations


def save_logistic(model, bundle_dir, metadata, *, version: str, name: str = "flowguard-logistic"):
    raise NotImplementedError


def load_logistic(bundle_dir):
    raise NotImplementedError
