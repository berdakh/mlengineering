# Mutant: overwrites_frozen_manifest

**The mistake.** `save_splits` (and therefore `flowguard split`) replaces an existing manifest
without complaint. Re-running the command with another seed after looking at results quietly changes
which experiments are "test"; every earlier number now refers to a split that no longer exists.

**Why a learner writes it.** Overwriting outputs is the normal behaviour of scripts.

**Caught by.** `test_a_frozen_manifest_is_not_silently_replaced`, `test_cli_creates_a_valid_manifest_and_refuses_to_overwrite`.
