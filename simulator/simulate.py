"""Sensor simulator.

Generates realistic temperature/humidity readings and POSTs them to the
ingestion API on an interval. Values follow a daily sinusoidal cycle
(warmest mid-afternoon, humidity inversely correlated) plus Gaussian noise,
so the dashboard charts look like real sensors instead of white noise.

Deliberately standalone: only requests + stdlib, no app imports, so it can
run anywhere (laptop, EC2 host, or as the `simulator` compose service).

    python simulator/simulate.py --url http://localhost:8001 --interval 5
    python simulator/simulate.py --once          # one round, then exit
"""

import argparse
import logging
import math
import os
import random
import time

import requests

log = logging.getLogger("simulator")

# Each sensor: a base level, how far the daily cycle swings it, noise, and
# where its peak sits in the day (phase_hours=14 -> hottest at 2pm).
SENSORS = [
    {"sensor_id": "temp-001", "sensor_type": "temperature",
     "base": 26.0, "amplitude": 6.0, "noise": 0.4, "phase_hours": 14},
    {"sensor_id": "temp-002", "sensor_type": "temperature",
     "base": 24.0, "amplitude": 5.0, "noise": 0.5, "phase_hours": 15},
    # Negative amplitude: humidity bottoms out when temperature peaks.
    {"sensor_id": "hum-001", "sensor_type": "humidity",
     "base": 62.0, "amplitude": -14.0, "noise": 1.5, "phase_hours": 14},
    {"sensor_id": "hum-002", "sensor_type": "humidity",
     "base": 58.0, "amplitude": -11.0, "noise": 2.0, "phase_hours": 15},
]

# Clamp to the same physical ranges the API enforces.
CLAMP = {"temperature": (-40.0, 85.0), "humidity": (0.0, 100.0)}


def generate_value(spec: dict, t: time.struct_time) -> float:
    hour_frac = t.tm_hour + t.tm_min / 60.0
    daily = math.sin(2 * math.pi * (hour_frac - spec["phase_hours"]) / 24.0 + math.pi / 2)
    value = spec["base"] + spec["amplitude"] * daily + random.gauss(0, spec["noise"])
    lo, hi = CLAMP[spec["sensor_type"]]
    return round(max(lo, min(hi, value)), 2)


def send_round(url: str) -> int:
    """POST one reading per sensor. Returns how many succeeded."""
    ok = 0
    now = time.localtime()
    for spec in SENSORS:
        payload = {
            "sensor_id": spec["sensor_id"],
            "sensor_type": spec["sensor_type"],
            "value": generate_value(spec, now),
        }
        try:
            resp = requests.post(f"{url}/sensors/readings", json=payload, timeout=5)
            resp.raise_for_status()
            log.info("sent %s=%s", payload["sensor_id"], payload["value"])
            ok += 1
        except requests.RequestException as e:
            # API may be restarting (deploys) -- log and keep going.
            log.warning("failed to send %s: %s", payload["sensor_id"], e)
    return ok


def main() -> None:
    parser = argparse.ArgumentParser(description="IoT sensor simulator")
    parser.add_argument("--url", default=os.getenv("API_URL", "http://localhost:8001"),
                        help="Base URL of the ingestion API")
    parser.add_argument("--interval", type=float,
                        default=float(os.getenv("SIM_INTERVAL_SECONDS", "5")),
                        help="Seconds between rounds")
    parser.add_argument("--once", action="store_true",
                        help="Send a single round of readings and exit")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    log.info("simulating %d sensors -> %s every %ss", len(SENSORS), args.url, args.interval)

    while True:
        send_round(args.url)
        if args.once:
            break
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
