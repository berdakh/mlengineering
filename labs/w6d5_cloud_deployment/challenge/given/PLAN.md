# Deployment plan: demandcast-api demo (draft by a colleague, for your review)

> Hi! Could you review this before I run it tomorrow morning? The regional managers want to try the
> forecast API on Thursday and Friday. I kept it simple so it just works. The machine-readable version
> is `plan.json` next to this file. Thanks! (SYNTHETIC scenario: the people and the service are invented.)

1. **Access.** I created an IAM user `deploy-bot` with `AdministratorAccess` so nothing fails on
   permissions, made an access key, and put it in `config/aws_credentials` in our repo so the whole
   team can deploy. The repo is private.
2. **Image.** Build and push to ECR as `demandcast:latest`, so the service always picks up the newest
   build. I turned scanning off because it slowed the push down.
3. **Model.** The model file (`model.npz`, 40 MB) goes into an S3 bucket `demandcast-models-demo`. I
   made the bucket public-read so the container can download it without any credentials setup.
4. **Compute.** ECS on Fargate, 1 vCPU / 2 GB, two tasks for high availability.
5. **Network.** Port 8080 open to 0.0.0.0/0, because the managers work from different offices and
   home. They will get the task IPs by e-mail.
6. **Logs.** CloudWatch log group `/ecs/demandcast`. I did not set a retention, so we keep everything.
7. **Cost.** Should be small, it is only two days. I did not set up a budget, we never had problems.
8. **Afterwards.** I will delete things in the console when I have time.
