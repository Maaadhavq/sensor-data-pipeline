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

## API (Phase 1)

| Method | Path                | Description                          |
|--------|---------------------|--------------------------------------|
| POST   | `/sensors/readings` | Ingest one reading                   |
| GET    | `/sensors/latest`   | Most recent reading per sensor       |
| GET    | `/health`           | Liveness probe                       |
| GET    | `/docs`             | Interactive Swagger UI               |

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
- [ ] Phase 2 — sensor simulator + hourly transformation job + S3 Parquet archival
- [ ] Phase 3 — analytics endpoints (`/insights/hourly`, `/insights/summary`) + Vercel dashboard
- [ ] Phase 4 — architecture diagram, API docs, demo workflow, presentation
