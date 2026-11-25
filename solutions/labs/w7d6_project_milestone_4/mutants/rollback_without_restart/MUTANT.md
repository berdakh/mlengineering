# Mutant: rollback_without_restart

The rollback moves the registry's CURRENT pointer but does not restart the service. The registry says the old model; /version and every answer still come from the bad one. A rollback is complete only after restart and a /version check.
