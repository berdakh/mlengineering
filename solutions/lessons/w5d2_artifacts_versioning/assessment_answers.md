# W5D2 assessment: model answers

## Reasoning questions

**1. "The bucket is private."** (a) Access control protects against outsiders, not against a
compromised CI job, a mistaken upload from another project, or a colleague's laptop with write access.
Any of them puts code on every machine that loads the model. (b) Even untampered, a pickle couples
the artifact to the exact class layout and library versions of the code that wrote it. A refactor or
library upgrade breaks loading or, worse, changes behaviour silently. Acceptable: a short-lived cache
written and read by the same process and version, never shared, or a library whose format is a pickle
(some torch checkpoints) loaded with the library's restricted loader (`torch.load(weights_only=True)`)
and only from your own pipeline.
*Common incorrect answer.* "Pickle is fine if you checksum it." A checksum proves the bytes are the
ones that were saved, not that what was saved is harmless.

**2. Checksums next to the files.** They protect against *accidental* change: partial copies, sync
conflicts, a hand edit, bit rot, a file added by a well-meaning script. Against a deliberate attacker
they protect nothing, since the attacker rewrites them. That is what the `rewrite_checksums` helper
in the checks does. Against tampering, add a signature over `checksums.json` with a key the
attacker does not have (e.g. Sigstore/cosign, GPG), or keep the digests in a separate system the
attacker cannot write (the registry database, an append-only log), and verify against that.

**3. Immutability.** Predictions, audit logs, evaluation reports and incident reviews record "made by
flowguard-flowrate 1.0.0". If 1.0.0 can change, every such record silently refers to a different
function, and rollback to 1.0.0 may not restore what was running before. The pointer answers "what
is live now"; the immutable version answers "what was live then". Rollback is then a one-line pointer
change to a known artifact.

**4. Format vs model version.** The bundle *format* describes how files are laid out and interpreted.
Adding a field that old loaders ignore is a backwards-compatible format change. Either keep
`format_version` 1 and document the optional field, or adopt `MAJOR.MINOR` for the format and bump
MINOR, so old loaders still accept it and new ones can rely on it. A field that changes meaning
requires a MAJOR format bump, so old loaders refuse. The model version (1.0.0) changes only if the
model changes: a re-save with identical scores is at most a PATCH.

**5. Cost of the safe format.** About 2.2 KB and 0.2 ms per load. That matters only if models are
loaded per request (never do that; load once at start-up) or if thousands of per-entity models are
loaded in a loop. Then batch the loads, or keep weights in one array file with an index, but still
without pickle. For a service that loads at start-up, the cost is irrelevant.

## Design-choice explanation: model answer

The logistic candidate's state is 16 coefficients and an intercept. Together with the calibration
rule, the clip and the feature layout, they are the whole decision function. Storing exactly that:

* makes loading incapable of running code;
* makes the artifact independent of scikit-learn's internal object layout, so a library upgrade
  cannot break loading;
* lets the loader check the feature layout by name, which `joblib.dump` would not record;
* makes the artifact readable in a diff.

The cost is a 30-line loader that re-implements `decision_function`, plus a parity test against the
trained object (identical to 0 on the real test runs). For a model whose state is a large tree
ensemble or a neural network, re-implementing inference is error-prone. There I would use a
restricted, inspectable format (skops for scikit-learn, `state_dict` + `torch.load(weights_only=True)`,
or ONNX for a cross-runtime graph), pin the training library version, and keep the same checksums,
format version and parity test.

## Interview rep rubric (system design: model registry)

| Level | What the answer contains |
|---|---|
| Strong | A registered model = immutable versioned artifact (weights + preprocessing state + threshold + input schema + model card with metrics and intervals + training data hash + code commit + library versions), checksummed and ideally signed. A registry service or bucket layout `name/version/`, metadata in a database, aliases or stages (`current`/`production`, `staging`) as mutable pointers. Services resolve the alias at start-up (or on a signal), log the resolved version with every prediction, and expose it on a health endpoint. Promotion goes through gates: offline evaluation against the current model on frozen data, then shadow or canary. Rollback = repoint the alias, with no rebuild. Retraining writes a new version and never overwrites. Lineage: the version links to the data snapshot and code commit, so "which model made prediction X" is a log lookup. Mentions access control and who may promote. |
| Adequate | Versioned artifacts and a "latest" pointer, rollback by pointer, but no input schema or lineage in the artifact, or no logging of the version per prediction. |
| Weak | "Save the model to S3 with a timestamp and load the newest one": no immutability, no promotion step, no way to answer the audit question. |

Worked answer, abridged. "Every training run produces a bundle: weights, preprocessing state,
threshold, input schema, model card, data and code hashes. CI registers it under `name/version` with
checksums and a signature, and it is never overwritten. Promotion moves an alias after an offline
comparison with the current model and a shadow period; rollback moves it back. Services resolve the
alias at start-up, refuse a bundle whose schema or format they do not support, and log the version with
each prediction. A month later, the log gives the version and the version gives everything."
