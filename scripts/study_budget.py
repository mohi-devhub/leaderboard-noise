"""Forecast from measured pilot work and enforce conservative per-model budget gates."""

from math import ceil


def forecast_model(pilot, factor, n_items=500, timing_items=100, repetitions=3):
    metas = [arm["metadata"] for arm in pilot["arms"]]
    stochastic = sum(
        t["elapsed_seconds"] for meta in metas for t in meta["timings"] if t["run_id"] == "sampling"
    )
    greedy = sum(
        t["elapsed_seconds"] for meta in metas for t in meta["timings"] if t["run_id"] != "sampling"
    )
    decode = factor * (
        stochastic * n_items / 100 + greedy * (n_items + repetitions * timing_items) / 100
    )
    expected = decode + 200  # Six fresh model loads, smoke checks, and downloads.
    ceiling = ceil(expected * 1.25 + 120)
    return {"forecast_seconds": expected, "execution_limit_seconds": ceiling}


def require_headroom(spent, next_reservation, cap=12.0, batch_threshold=5.0):
    if spent < 0 or next_reservation <= 0:
        raise ValueError("invalid budget amounts")
    if next_reservation > batch_threshold:
        raise ValueError("next model exceeds the $5 batch approval threshold")
    if spent + next_reservation > cap:
        raise ValueError("next model would cross the $12 project total")


def resource_estimate(seconds, hourly, extra=0):
    if seconds < 0 or hourly <= 0 or extra < 0:
        raise ValueError("invalid resource accounting inputs")
    return seconds * hourly / 3600 + extra
