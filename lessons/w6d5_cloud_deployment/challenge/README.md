# w6d5 challenge: review a colleague's deployment plan (cost and risk)

**Time:** 30-45 minutes, unassisted. **Scenario (SYNTHETIC):** a colleague asks you to review their
plan for a two-day demo of a demand-forecast API before they run it tomorrow. Read
[`given/PLAN.md`](given/PLAN.md) and its machine-readable form [`given/plan.json`](given/plan.json).

This is the transfer task: a different service, a different team, the same cost and security
reasoning as the lab. You are reviewing a *plan*; nothing is deployed and no AWS access is involved.

## What to hand in

1. **`challenge/plan_fixed.json`** (the starter is an unchanged copy of the colleague's plan): a
   corrected plan in the same schema that you would approve. Keep every key; change values; add keys
   where the corrected plan needs them (for example a `budget` object or `teardown` entries).
2. **`challenge/REVIEW.md`**: the review you would send back, under the headings in the starter. For
   each problem: what is wrong, the concrete risk or cost, and the change you require. End with a
   decision (go / go with changes / no-go) and its conditions. Write it for the colleague: direct,
   specific, not condescending.

## Acceptance criteria

`python wb.py check w6d5 --challenge` checks the corrected plan and the review's structure:

* credentials come from IAM Identity Center (`"mode": "sso"`) with a named, non-administrator
  permission set or role; no key material, no stored credential file, no IAM user for deployment;
* a budget exists before anything is created: `limit_usd` > 0 and at least one alert at or below
  100 % of the limit;
* the registry is immutable, scans on push, and the image tag is a git SHA;
* the model artifacts are not public: either the bucket blocks public access and the task reads it with
  its task role, or the bucket is gone and the model is baked into the image;
* no inbound rule admits more than one address (no `0.0.0.0/0`, no `::/0`, every CIDR a `/32`);
* logs have a retention between 1 and 30 days;
* the teardown lists every resource in `resources`, by type and name;
* the review has every heading filled in (no TODO) and the decision section states go, go with changes,
  or no-go.

The checks cannot judge whether your reasoning is good; the rubric in
`solutions/lessons/w6d5_cloud_deployment/assessment_answers.md` does (open it after you finish).
