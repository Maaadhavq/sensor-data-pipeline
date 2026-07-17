# API Documentation

Interactive docs are auto-generated and always current:
**`/docs`** (Swagger UI, try requests in the browser) and **`/redoc`**.
This page is the quick reference with real request/response examples.

**Base URLs**

| Environment | URL |
|---|---|
| Local dev | `http://localhost:8001` |
| EC2 | `http://<ec2-ip>:8001` |
| Via dashboard proxy | `https://<vercel-app>/api` |

**Sensor types**

| `sensor_type` | Unit | Accepted range |
|---|---|---|
| `temperature` | `celsius` | −40 … 85 |
| `humidity` | `percent` | 0 … 100 |

---

## POST /sensors/readings

Ingest one reading. `recorded_at` is optional — the server fills it with the
current UTC time when omitted.

```bash
curl -X POST http://localhost:8001/sensors/readings \
  -H "Content-Type: application/json" \
  -d '{"sensor_id": "temp-001", "sensor_type": "temperature", "value": 24.7}'
```

**201 Created**

```json
{
  "id": 1,
  "sensor_id": "temp-001",
  "sensor_type": "temperature",
  "value": 24.7,
  "unit": "celsius",
  "recorded_at": "2026-07-16T16:15:11.705271",
  "ingested_at": "2026-07-16T16:15:11.712791"
}
```

**422 Unprocessable Entity** — unknown `sensor_type`, or value outside the
physical range:

```json
{
  "detail": [{
    "type": "value_error",
    "loc": ["body"],
    "msg": "Value error, humidity value 130.0 outside plausible range [0.0, 100.0]"
  }]
}
```

## GET /sensors/latest

Most recent stored reading for every sensor — the real-time view.

```bash
curl http://localhost:8001/sensors/latest
```

**200 OK** — one entry per sensor:

```json
[
  {"id": 2, "sensor_id": "hum-001",  "sensor_type": "humidity",    "value": 58.2, "unit": "percent", "recorded_at": "...", "ingested_at": "..."},
  {"id": 1, "sensor_id": "temp-001", "sensor_type": "temperature", "value": 24.7, "unit": "celsius", "recorded_at": "...", "ingested_at": "..."}
]
```

## GET /insights/hourly

Hourly aggregates for charting, oldest first.

| Query param | Default | Constraints | Meaning |
|---|---|---|---|
| `hours` | 24 | 1–168 | Look-back window |
| `sensor_id` | — | — | Filter to one sensor |

```bash
curl "http://localhost:8001/insights/hourly?hours=24&sensor_id=temp-001"
```

**200 OK**

```json
[
  {"sensor_id": "temp-001", "sensor_type": "temperature", "hour_start": "2026-07-16T15:00:00",
   "avg_value": 23.53, "min_value": 22.36, "max_value": 24.7, "reading_count": 6}
]
```

## GET /insights/summary

Current state per sensor: the latest raw reading merged with 24h statistics
from the aggregates table. The 24h average is **weighted by reading count**,
so an hour with 30 readings counts three times as much as an hour with 10.
Sensors with readings but no aggregates yet (job hasn't run) appear with the
24h fields as `null`.

```bash
curl http://localhost:8001/insights/summary
```

**200 OK**

```json
[
  {"sensor_id": "temp-001", "sensor_type": "temperature", "unit": "celsius",
   "latest_value": 22.36, "latest_at": "2026-07-16T16:59:05.274245",
   "avg_24h": 26.123, "min_24h": 19.17, "max_24h": 32.68, "reading_count_24h": 140}
]
```

## Meta

| Endpoint | Purpose |
|---|---|
| `GET /` | API name, version, doc links |
| `GET /health` | Liveness probe → `{"status": "ok"}` |
