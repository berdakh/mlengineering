# Mutant: rollback_by_tag

Deploys `image:release` instead of `image@digest`. A tag is a movable pointer: if the tag was
re-pushed (or the registry allows overwrite) the rollback runs something nobody tested.
