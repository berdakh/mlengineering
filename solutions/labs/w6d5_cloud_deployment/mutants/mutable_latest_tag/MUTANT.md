# Mutant: mutable_latest_tag

Pushes `:latest` into a MUTABLE repository. Two deployments of `latest` can run different code;
rollback has nothing to point at; the task definition no longer says which build it runs.
