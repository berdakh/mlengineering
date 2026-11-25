# Mutant: reloads_model_per_request

Loads the bundle inside `/predict`. It works in a demo and costs a disk read and checksum per
request; worse, a deployment that replaces the files on disk changes the model in the middle of
serving, and a missing file turns every request into a 503 (or 500).
