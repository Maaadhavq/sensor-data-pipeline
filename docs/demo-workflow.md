# Demo Workflow

The scripted 5-minute demo that proves every curriculum feature live.
Do the checklist the night before; the demo itself is copy-paste.

## Pre-demo checklist (night before)

- [ ] EC2: both containers up — `docker compose -f docker-compose.prod.yml ps`
      shows `api` and `simulator` running (simulator = continuous live data).
- [ ] Cron installed: `crontab -l` shows the hourly transform line.
- [ ] At least 24h of aggregates exist (the cron has been running overnight),
      or run `python -m scripts.seed_demo_data` once for instant history.
- [ ] Vercel dashboard loads and the "live · updated …" clock ticks.
- [ ] S3 console: the bucket shows `raw/year=…/hour=…/readings.parquet`
      partitions accumulating.
- [ ] Have two browser tabs ready: the Vercel dashboard and `/docs` on EC2.

## The demo (in order)

**1. Start on the dashboard (Vercel URL) — the deliverable.**
Point out the live indicator updating every 10 seconds, the four sensor
cards, the daily temperature/humidity cycles in the charts. Hover a chart to
show the tooltip. *(~1 min)*

**2. Show where the data comes from — the simulator.**

```bash
ssh ubuntu@<ec2-ip>
docker compose -f docker-compose.prod.yml logs simulator --tail 5
```

Live log lines: `sent temp-001=24.7` every 5 seconds. *(~30 s)*

**3. Ingestion API + validation (Swagger `/docs` tab).**
POST a valid reading via *Try it out* → 201 with server-filled `unit` and
`recorded_at`. Then POST `{"sensor_type": "humidity", "value": 130}` →
422 "outside plausible range" — bad data never reaches the DB. *(~1 min)*

**4. Real-time endpoint.**

```bash
curl http://<ec2-ip>:8001/sensors/latest
```

Values match what the dashboard cards show. *(~30 s)*

**5. The transformation job + data lake.**

```bash
docker compose -f docker-compose.prod.yml exec -T api python -m jobs.transform
```

Log output: `N readings -> 4 aggregate rows, archived to s3://…`.
Run it **twice** — same 4 rows, not 8: idempotency, live. Then flip to the
S3 console tab and show the Hive-partitioned Parquet files. *(~1.5 min)*

**6. Close the loop.**
Back on the dashboard: refresh — the newest hour appears in the charts.
Ingestion → storage → transformation → lake → insights → UI, end to end.
*(~30 s)*

## If something breaks

| Symptom | First move |
|---|---|
| Dashboard cards empty | `curl http://<ec2-ip>:8001/health` — is the API up? `docker compose ... ps` |
| Charts empty but cards live | Transform hasn't run: trigger step 5 manually |
| Vercel can't reach API | EC2 security group must allow :8001; check `API_PROXY_TARGET` env var |
| Simulator silent | `docker compose ... restart simulator` |

## Feature → proof map (for the grader)

| Curriculum feature | Where it's proven |
|---|---|
| Sensor data ingestion | Step 3 (POST + validation) |
| Real-time API | Step 4 (`/sensors/latest`) |
| S3 data lake | Step 5 (Parquet partitions in console) |
| Data transformation jobs | Step 5 (live run, idempotent) |
| Data insights | Steps 1 & 6 (`/insights/*` feeding the dashboard) |
| Deployment URL (Vercel) | Step 1 |
