# Sensor Data Pipeline

Week 8 capstone: an IoT sensor data pipeline with an analytics dashboard.
Simulated temperature/humidity sensors stream readings into a FastAPI
ingestion service; a scheduled transformation job aggregates them into
hourly analytics (RDS) and archives raw batches to an S3 data lake as
Parquet; a Next.js dashboard on Vercel charts the insights.

## Architecture

```
[Sensor Simulator]  --POST readings-->  [Ingestion API (FastAPI, EC2/Docker)]
                                                |
                                                v
                                      [RDS Postgres: raw_readings]
                                                |
                                                v
                              [Transformation job: hourly aggregates]
                                    /                        \
                                   v                          v
                        [S3 data lake: Parquet]      [RDS: hourly_aggregates]
                                                                |
                                                                v
                                              [Analytics API: GET /insights, /latest]
                                                                |
                                                                v
                                          [Frontend dashboard (Next.js, Vercel)]
```

## API

| Method | Path                | Description                                        |
|--------|---------------------|----------------------------------------------------|
| POST   | `/sensors/readings` | Ingest one reading                                 |
| GET    | `/sensors/latest`   | Most recent reading per sensor (real-time)         |
| GET    | `/insights/hourly`  | Hourly aggregates for charting (`?hours=`, `?sensor_id=`) |
| GET    | `/insights/summary` | Latest value + weighted 24h stats per sensor       |
| GET    | `/health`           | Liveness probe                                     |
| GET    | `/docs`             | Interactive Swagger UI                             |

Sensor types: `temperature` (celsius, -40..85) and `humidity` (percent, 0..100).
Out-of-range or unknown-type readings are rejected with a 422.

## Run locally

```bash
python -m venv .venv && .venv\Scripts\activate   # Windows
pip install -r requirements.txt
copy .env.example .env                            # then edit DATABASE_URL
uvicorn app.main:app --reload --port 8001
```

Or with Docker (brings up its own Postgres on host port 5433):

```bash
docker compose up --build
```

## Simulator (Phase 2)

Four fake sensors (2x temperature, 2x humidity) with a realistic daily
cycle -- warmest mid-afternoon, humidity inversely correlated -- plus noise:

```bash
python simulator/simulate.py --url http://localhost:8001 --interval 5
python simulator/simulate.py --once     # single round, for testing
```

In production it runs as the `simulator` compose service, so live data
flows continuously during the demo. Locally: `docker compose --profile sim up`.

## Transformation job (Phase 2)

Aggregates one hour of raw readings (avg/min/max/count per sensor) into
`hourly_aggregates` and archives the raw batch as Parquet -- to the S3 data
lake when `S3_BUCKET_NAME` is set, otherwise to `data/lake/` locally.
Hive-style partitions: `raw/year=2026/month=07/day=16/hour=15/readings.parquet`.

```bash
python -m jobs.transform                       # last completed hour
python -m jobs.transform --hour 2026-07-16T14  # backfill a specific hour (UTC)
```

Idempotent: re-running an hour upserts aggregates (unique on
sensor_id + hour_start) and overwrites the same Parquet partition.

Scheduled on EC2 via cron, 5 minutes past each hour:

```cron
5 * * * * cd ~/sensor-data-pipeline && docker compose -f docker-compose.prod.yml exec -T api python -m jobs.transform >> ~/transform.log 2>&1
```

## Tests

```bash
pytest -v
```

Tests run against in-memory SQLite via a dependency override -- no
Postgres needed (this is what CI runs).

## Deployment

Same CI/CD pattern as employee-management-api: push to `main` runs tests,
builds/pushes the Docker image, then deploys to EC2 over SSH using
`docker-compose.prod.yml` (host port **8001**, alongside the employee API
on 8000). Required repo secrets: `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`,
`EC2_HOST`, `EC2_SSH_KEY`.

## Roadmap

- [x] Phase 1 — ingestion + real-time API, tables, Docker, CI/CD
- [x] Phase 2 — sensor simulator + hourly transformation job + S3 Parquet archival
- [x] Phase 3a — analytics endpoints (`/insights/hourly`, `/insights/summary`)
- [x] Phase 3b — Next.js dashboard ([sensor-dashboard](https://github.com/Maaadhavq/sensor-dashboard)) on Vercel
- [x] Phase 4 — [architecture](docs/architecture.md) · [API docs](docs/api.md) · [demo workflow](docs/demo-workflow.md) · [deployment](docs/deployment.md) · presentation
