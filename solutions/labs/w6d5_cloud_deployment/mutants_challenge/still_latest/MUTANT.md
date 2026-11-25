# Mutant: still_latest

Fixes everything except the image tag: `latest` with an immutable repository. Immutability then
means the second push of `latest` fails, and the deployment still does not say which build runs.
