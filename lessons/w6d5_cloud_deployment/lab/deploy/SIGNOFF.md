# Sign-off before any live AWS step

`python deploy/aws_deploy.py ... --live` refuses to run until every box below is ticked (`- [x]`).
Tick a box only when the statement is true **today**. Ticking boxes is a decision you are making
about your own money and your own account; nothing in this course makes it for you.

## Required

- [ ] I have read deploy/BRIEFING.md in full, today.
- [ ] I am signed in with short-lived credentials from IAM Identity Center (`aws sso login`); no access keys are stored on this machine for this account.
- [ ] `aws sts get-caller-identity` shows the account and role I intend to use.
- [ ] I have checked the current prices of ECS on Fargate, ECR, CloudWatch Logs and public IPv4 addresses for my region on the official AWS pricing pages, and I accept the cost.
- [ ] I have read the generated deploy and teardown scripts (the dry-run output) line by line.
- [ ] I will run the teardown today, and I have put a reminder in my calendar.

## Public access (only needed when network.allow_public = true)

- [ ] I understand that the service will be reachable from more than my own IP address.
- [ ] Nobody but me will rely on it, and it carries no real or private data.
- [ ] I will tear it down within the same day.
