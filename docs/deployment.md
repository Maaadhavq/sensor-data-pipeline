# Deployment Runbook — Sensor Data Pipeline

Takes the project from "repos on GitHub" to a live Vercel URL. Follow the
steps in order; every command is copy-paste ready. Commands are labelled
**PowerShell** (your Windows laptop) or **EC2 (Ubuntu)** (after SSH).
Everything reuses the Week 4 footprint — total marginal cost ≈ $0.

Time: ~30–40 minutes.

## Step 0 — Have these five things in hand

| # | Item | Where to find it |
|---|---|---|
| 1 | EC2 public IP | AWS console → EC2 → Instances (the Week 4 instance) |
| 2 | RDS endpoint + master password | AWS console → RDS → Databases (same instance as employee_db) |
| 3 | Docker Hub username + access token | hub.docker.com → Account Settings → Security |
| 4 | EC2 SSH private key file | The same `.pem` used for the employee API deploys |
| 5 | A GitHub account logged into `gh` | `gh auth status` (already done if you pushed the repos) |

Wherever you see `<EC2_IP>`, `<RDS_ENDPOINT>`, `<RDS_PASSWORD>`, or
`<DOCKERHUB_USERNAME>` below, substitute yours.

---

## Step 1 — GitHub Actions secrets (PowerShell)

Same four secrets as the employee API repo, set on the new repo:

```powershell
cd C:\Users\madha\Downloads\sensor-data-pipeline
gh secret set DOCKERHUB_USERNAME --body "<DOCKERHUB_USERNAME>"
gh secret set DOCKERHUB_TOKEN                     # paste token when prompted
gh secret set EC2_HOST --body "<EC2_IP>"
gh secret set EC2_SSH_KEY < path\to\your-key.pem
```

**Verify:** `gh secret list` shows all four.

## Step 2 — Put your real Docker Hub username in the prod compose file (PowerShell)

`docker-compose.prod.yml` currently guesses `maaadhavq`. Fix the fallback:

```powershell
cd C:\Users\madha\Downloads\sensor-data-pipeline
# edit docker-compose.prod.yml: replace both occurrences of
#   ${DOCKERHUB_USERNAME:-maaadhavq}
# with
#   ${DOCKERHUB_USERNAME:-<your real username>}
git add docker-compose.prod.yml
git commit -m "Set real Docker Hub username in prod compose"
git push
```

**Verify:** this push re-runs CI — with Step 1's secrets in place, all three
jobs should now go green *except* the final deploy step, which needs Step 4
first (the repo isn't cloned on EC2 yet). That's expected; keep going.

## Step 3 — AWS: database, bucket, firewall (console + PowerShell)

**3a. New database on the existing RDS instance** (does NOT touch employee_db):

```powershell
psql -h <RDS_ENDPOINT> -U postgres -c "CREATE DATABASE sensor_db;"
```

(No psql on Windows? Run it from EC2 in Step 4 instead — same command.)

**3b. S3 bucket for the data lake** — console → S3 → *Create bucket*:
name `maaadhavq-sensor-lake` (must be globally unique), region **ap-south-1**,
keep *Block all public access* ON.

**3c. Let EC2 write to it** — console → IAM → Roles → the Week 4 EC2 role →
add this to its policy (or attach as a new inline policy):

```json
{
  "Effect": "Allow",
  "Action": ["s3:PutObject"],
  "Resource": "arn:aws:s3:::maaadhavq-sensor-lake/*"
}
```

**3d. Open port 8001** — console → EC2 → Security Groups → the instance's
group → *Edit inbound rules* → Add rule: Custom TCP, port **8001**,
source `0.0.0.0/0`.

**Verify:** nothing to test yet — Step 4 exercises all of it.

## Step 4 — EC2: clone, configure, start (EC2 Ubuntu)

```bash
ssh -i path/to/your-key.pem ubuntu@<EC2_IP>

git clone https://github.com/Maaadhavq/sensor-data-pipeline.git
cd sensor-data-pipeline
cp .env.example .env
nano .env
```

Set `.env` to exactly this (with your values):

```ini
DATABASE_URL=postgresql://postgres:<RDS_PASSWORD>@<RDS_ENDPOINT>:5432/sensor_db
ENVIRONMENT=production
AWS_REGION=ap-south-1
S3_BUCKET_NAME=maaadhavq-sensor-lake
```

Then start both containers (API + simulator):

```bash
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

**Verify (three checks):**

```bash
curl localhost:8001/health                                   # {"status":"ok"}
docker compose -f docker-compose.prod.yml logs simulator --tail 3   # "sent temp-001=..."
curl localhost:8001/sensors/latest                           # readings appearing
```

And from your **laptop** (proves the security group rule):

```powershell
curl http://<EC2_IP>:8001/health
```

## Step 5 — Cron: the hourly transformation job (EC2 Ubuntu)

```bash
crontab -e
```

Add this line, save, exit:

```cron
5 * * * * cd ~/sensor-data-pipeline && docker compose -f docker-compose.prod.yml exec -T api python -m jobs.transform >> ~/transform.log 2>&1
```

Then run the job once by hand so you don't wait an hour:

```bash
cd ~/sensor-data-pipeline
docker compose -f docker-compose.prod.yml exec -T api python -m jobs.transform --hour $(date -u +%Y-%m-%dT%H)
```

**Verify:** the command logs `N readings -> M aggregate rows, archived to s3://…`,
and the S3 console shows `raw/year=…/readings.parquet` in the bucket.

## Step 6 — Seed 24h of history (EC2 Ubuntu, optional but recommended)

So the dashboard charts open with a full day of curves instead of one dot:

```bash
docker compose -f docker-compose.prod.yml exec -T api python -m scripts.seed_demo_data
```

**Verify:** `curl "localhost:8001/insights/hourly?hours=24"` returns ~96 rows.

## Step 7 — Vercel: the dashboard (browser)

1. <https://vercel.com> → sign in with GitHub → **Add New → Project** →
   import **`sensor-dashboard`**. Framework auto-detects as Next.js —
   defaults are all fine.
2. Before (or after) the first deploy: **Settings → Environment Variables** →
   add `API_PROXY_TARGET` = `http://<EC2_IP>:8001` (all environments).
   If you added it after deploying, hit **Redeploy**.
3. Open the deployment URL.

**Verify:** the four sensor cards show values, the "live · updated …" clock
ticks every 10 s, and both charts have curves (from Step 6).

> If the deployment URL is not `sensor-dashboard.vercel.app`, update it on
> slides 6 and 11 of `docs/presentation.pptx` and in the README.

## Step 8 — Prove CI/CD end to end (PowerShell)

Now that EC2 has the repo cloned, the full pipeline can run:

```powershell
cd C:\Users\madha\Downloads\sensor-data-pipeline
gh workflow run "CI/CD Pipeline" --ref main   # or just push any commit
gh run watch
```

**Verify:** all three jobs green — *Run tests → Build and push Docker image →
Deploy to EC2*. From now on, every push to `main` ships automatically.

---

## Done — deliverable URLs

| Deliverable | URL |
|---|---|
| GitHub (pipeline) | <https://github.com/Maaadhavq/sensor-data-pipeline> |
| GitHub (dashboard) | <https://github.com/Maaadhavq/sensor-dashboard> |
| API + Swagger docs | `http://<EC2_IP>:8001/docs` |
| **Deployment URL (Vercel)** | your Step 7 URL |

Next: walk `docs/demo-workflow.md` once, the night before presenting.

## Teardown after grading

Remove the cron line (`crontab -e`), then on EC2:
`docker compose -f docker-compose.prod.yml down`. Empty + delete the S3
bucket, pause the Vercel project. The shared EC2/RDS teardown is governed
by the Week 4 runbook.
