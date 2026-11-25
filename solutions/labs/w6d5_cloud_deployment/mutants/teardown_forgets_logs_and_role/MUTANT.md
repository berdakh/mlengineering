# Mutant: teardown_forgets_logs_and_role

The teardown removes the obvious, billed resources (service, cluster, repository) but not the log
group or the IAM role. Stored logs keep costing; an orphaned role with ECR and logs permissions is
exactly the kind of leftover that later gets reused for something it was never reviewed for.
