# Deployment — deltas from the Week 4 runbook

Everything from `employee-management-api/docs/aws-deployment.md` still
applies (same account, same EC2, same RDS). This page is only what's
**different** for the capstone. Total marginal cost: ~$0.

## 1. Database — new DB on the existing RDS instance

```bash
# from EC2 (or anywhere that can reach RDS)
psql -h <rds-endpoint> -U postgres -c "CREATE DATABASE sensor_db;"
```

Tables are created automatically on first API startup (`init_db()`).
`employee_db` is untouched.

## 2. S3 — one new bucket for the data lake

Console → S3 → Create bucket (e.g. `maaadhavq-sensor-lake`, ap-south-1,
block all public access). Extend the EC2 IAM role's policy to allow
`s3:PutObject` on `arn:aws:s3:::maaadhavq-sensor-lake/*`.

## 3. EC2 — second app on port 8001

```bash
# security group: add inbound rule TCP 8001 from 0.0.0.0/0
ssh ubuntu@<ec2-ip>
git clone https://github.com/Maaadhavq/sensor-data-pipeline.git
cd sensor-data-pipeline
cp .env.example .env   # set DATABASE_URL (RDS + sensor_db), ENVIRONMENT=production,
                       # S3_BUCKET_NAME, AWS_REGION
docker compose -f docker-compose.prod.yml up -d   # starts api + simulator
curl localhost:8001/health                        # {"status":"ok"}
```

## 4. Cron — the hourly transformation job

```bash
crontab -e
# add:
5 * * * * cd ~/sensor-data-pipeline && docker compose -f docker-compose.prod.yml exec -T api python -m jobs.transform >> ~/transform.log 2>&1
```

## 5. GitHub Actions — same four secrets as Week 4

`DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`, `EC2_HOST`, `EC2_SSH_KEY` in the
`sensor-data-pipeline` repo. Push to `main` = test → build → deploy.

## 6. Vercel — the dashboard

1. Push `sensor-dashboard` to GitHub, import it at vercel.com (defaults fine).
2. Project → Settings → Environment Variables:
   `API_PROXY_TARGET = http://<ec2-ip>:8001`
3. Deploy. The browser only ever talks to Vercel (https); Vercel's server
   proxies `/api/*` to EC2 over http — no mixed-content block, no CORS.

## Teardown after grading

Remove the cron line, `docker compose -f docker-compose.prod.yml down`,
delete the S3 bucket contents, and pause the Vercel project. The shared
EC2/RDS teardown is governed by the Week 4 runbook.
