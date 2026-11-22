# API compatibility policy for flowguard (reference)

## Versioning

The public contract has a schema name, `flowguard-api/<major>`, returned by `GET /version`
(`api_schema`). The major number changes only for a breaking change. The package version
(semantic versioning) and the model version change independently: a new model or a bug fix does not
change the API schema.

## What we promise clients

Within one major version we may, without notice: add endpoints (`GET /sites`); add *optional*
request fields with a default that keeps the old behaviour (`explain: false`); add response fields
(`latency_ms`); relax request constraints (accept longer `burn_in`); add new error responses for
inputs that were already invalid. Clients must ignore response fields they do not know.

## Breaking changes

Breaking: removing or renaming an endpoint, a response field or a success status; making a response
field optional or nullable; requiring a new request field; rejecting a request field that used to be
accepted; changing a field's type; tightening a constraint (`maxItems` 3600 -> 600). A breaking change
ships as a new major schema, served side by side with the old one (`/v2/predict` next to
`/predict`) for at least one release cycle (90 days for this project), announced in the CHANGELOG
with a migration note. The old version is removed only after its traffic, measured in the request
logs, has gone to zero or the owners of the remaining clients have agreed.

## How the promise is enforced

`challenge/test_contract.py` compares the OpenAPI document of the candidate build with the one
recorded for the last release (`openapi-v1.json`, committed). It runs in CI on every pull request;
any message from `breaking_changes` fails the build unless the major schema number was increased in
the same change. Behavioural tests (lab) still run: a schema can stay identical while the meaning of
a field changes (ddof, threshold inclusivity), and only behavioural tests catch that.

## Verdict on the proposed v2

Not backwards compatible. Breaking: `site_id` is required (every v1 request now gets 422);
`scores` renamed to `score` (v1 clients read a missing field); `burn_in` maxItems 3600 -> 600 (long
calibrations get 422). Non-breaking: `explain` (optional, default false), `latency_ms`, `GET /sites`.
Ship the useful parts as 0.6.0 without breaking v1: make `site_id` optional with a documented default
site; keep `scores` (add `score` only if there is a reason, and never remove `scores` within
`flowguard-api/1`); keep the 3600 limit, or move the limit to a new `/v2/predict`; keep the additions.
