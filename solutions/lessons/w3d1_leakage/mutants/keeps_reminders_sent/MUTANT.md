# Mutant: keeps_reminders_sent

Keeps `reminders_sent` (target leakage: reminders are sent after the due date). Everything else is correct, so the split is temporal and duplicates are removed, yet the reported AP is about 0.97 while production-like rows score near 0.29.
