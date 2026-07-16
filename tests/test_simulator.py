"""Simulator sanity checks: generated values always pass API validation."""

import time

from simulator.simulate import CLAMP, SENSORS, generate_value


def test_values_stay_in_physical_range_all_day():
    for hour in range(24):
        t = time.struct_time((2026, 7, 16, hour, 30, 0, 0, 0, -1))
        for spec in SENSORS:
            lo, hi = CLAMP[spec["sensor_type"]]
            for _ in range(50):  # noise is random -- sample repeatedly
                value = generate_value(spec, t)
                assert lo <= value <= hi, (spec["sensor_id"], hour, value)


def test_temperature_peaks_in_afternoon():
    spec = next(s for s in SENSORS if s["sensor_id"] == "temp-001")
    spec_no_noise = {**spec, "noise": 0}
    afternoon = time.struct_time((2026, 7, 16, 14, 0, 0, 0, 0, -1))
    night = time.struct_time((2026, 7, 16, 2, 0, 0, 0, 0, -1))
    assert generate_value(spec_no_noise, afternoon) > generate_value(spec_no_noise, night)
