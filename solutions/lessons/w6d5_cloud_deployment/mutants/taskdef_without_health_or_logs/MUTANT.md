# Mutant: taskdef_without_health_or_logs

Keeps the task definition from the starter: no `healthCheck` and no `logConfiguration`. ECS then only
knows whether the process is alive, not whether the model loaded, and the container's JSON logs go
nowhere; the first incident has no evidence.
