# flowguard runbook

Owner: TODO. Audience: whoever is on call for the plant monitoring stack.

Keep these section headings. Every alert in `configs/alerts.toml` needs its own `### <AlertName>` section
under "Alerts" with three labelled lines: **Meaning:**, **First actions:** and **Escalate:**.

## Service overview

TODO: what the service does, the model and its measured quality, the fallback and its cost, the endpoints,
where the artifacts live.

## Dashboards and queries

TODO: a table of questions an on-call engineer asks and the exact command that answers each.

## Alerts

### ServiceNotReady

TODO

## Common incidents

TODO

## Rollback

TODO: the exact commands, and how you know the rollback is complete.

## Escalation

TODO

## Known limitations

TODO
