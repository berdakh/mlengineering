# Mutant: rollback_to_running_image

Picks the most recent earlier `good` entry without checking that its digest differs from the
current one. After a configuration incident (same image, now failing) it 'rolls back' to the image
that is already running: the command succeeds and nothing changes.
