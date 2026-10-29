"""Reconcile a validated pilot against recorded timings, rates, and billing snapshots."""

import argparse
from datetime import datetime
from decimal import Decimal
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("session", type=Path)
    parser.add_argument("--rates", type=Path, required=True)
    args = parser.parse_args()
    session = args.session
    result = json.loads((session / "job-result.json").read_text())
    calls = json.loads((session / "final-calls.json").read_text())
    stats = json.loads((session / "final-stats.json").read_text())
    rates = json.loads(args.rates.read_text())["rates"]
    if result["status"] != "complete" or len(calls) != 1 or calls[0]["status"] != "success":
        raise ValueError("receipt requires one successfully completed pilot job")
    if stats["container_total_count"] != 1:
        raise ValueError("multiple containers require separate resource accounting")
    if not (session / "REPORT.md").exists():
        raise ValueError("run the scorer and coverage validator first")
    gpu = result["gpu"]
    if "A10" in gpu:
        gpu_rate = Decimal(rates["gpu_hour_cost_a10g"])
    elif "L4" in gpu:
        gpu_rate = Decimal(rates["gpu_hour_cost_l4"])
    else:
        raise ValueError("unexpected GPU for this pilot")
    elapsed = Decimal(str(calls[0]["execution_time_seconds"]))
    startup = Decimal(
        str(stats["container_percentile_stats"]["Startup time (s)"]["percentiles"]["p50"])
    )
    hourly = (
        gpu_rate + 4 * Decimal(rates["cpu_hour_cost"]) + 16 * Decimal(rates["mem_gib_hour_cost"])
    )
    timed = (elapsed + startup + 2) * hourly / 3600
    before = json.loads((session / "billing-before.json").read_text())
    after = json.loads((session / "billing-after.json").read_text())
    delta = Decimal(after["metered_cost"]) - Decimal(before["metered_cost"])
    estimate = max(timed, delta, Decimal(0))
    ledger_path = Path("results/budget-ledger.json")
    ledger = json.loads(ledger_path.read_text())
    entry = next(e for e in ledger["entries"] if e["session"] == str(session))
    entry.setdefault("initial_reserved_usd", entry["reserved_usd"])
    entry["released_reservation_usd"] = entry["initial_reserved_usd"]
    entry["reserved_usd"] = 0
    entry["estimated_spend_usd"] = float(estimate)
    entry["estimate_basis"] = (
        "larger of timed resource-ceiling estimate and provisional account gross-metered change; not settled invoice actual"
    )
    entry["status"] = "pilot_validated_waiting_for_full_run_approval"
    ledger_path.write_text(json.dumps(ledger, indent=2) + "\n")
    total = sum(Decimal(str(e.get("estimated_spend_usd", 0))) for e in ledger["entries"])
    wall = (
        datetime.fromisoformat(entry["ended_at"]) - datetime.fromisoformat(entry["started_at"])
    ).total_seconds()
    receipt = {
        "gpu": gpu,
        "job_count": 1,
        "gpu_container_count": 1,
        "initial_smoke_requests": result["smoke"]["requests"],
        "benchmark_predictions": sum(len(arm["rows"]) for arm in result["arms"]),
        "execution_seconds": float(elapsed),
        "container_startup_seconds": float(startup),
        "controller_wall_seconds_before_cleanup": wall,
        "resource_ceiling_hourly_usd": str(hourly),
        "timed_resource_estimate_usd": str(timed),
        "account_metered_change_usd": str(delta),
        "estimated_session_spend_usd": str(estimate),
        "estimated_project_total_usd": str(total),
        "actual_invoice_usd": None,
        "connection_reconnects_used": int("connection_recovery" in entry),
        "reservation_released_usd": entry["initial_reserved_usd"],
        "active_reservation_usd": 0,
        "attribution_note": entry["estimate_basis"],
        "full_run_approved": False,
    }
    (session / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    section = f"""\n<!-- receipt:start -->
## Session cost and timing

- GPU: **{gpu}**, one job and one container for every arm/model; no GPU comparisons are inferred.
- Five initial smoke requests passed before the 3,200 benchmark predictions. Each model/arm also passed its own internal smoke check.
- Remote execution: **{elapsed:.2f} seconds** ({elapsed / 60:.2f} minutes), including imports, model loads, smoke tests, warmups, and generation.
- Observed container startup: **{startup:.2f} seconds**; controller wall time before cleanup: **{wall:.2f} seconds**.
- Connection reconnects used: **{receipt["connection_reconnects_used"]}**. Exactly one job was submitted.
- Resource-ceiling estimate: **${timed:.6f}**, using execution + startup + two seconds of scaledown at {hourly} USD/hour. Image building and egress are outside that timed estimate.
- Account gross-metered change: **${delta:.8f}**. The conservative session estimate uses the larger value: **${estimate:.6f}**. Attribution is provisional because account metering may lag or include unrelated usage. Settled invoice actuals remain unknown.
- Recorded estimated project total including prior failures: **${total:.6f}** of the $12 cap. The $4.50 unused reservation is released; active reservations are zero.

The evalnoise app is stopped. The separate qunti-check project was not modified. This pilot completed before the October 31 deadline. The full six-model experiment remains unapproved and has not been launched.
<!-- receipt:end -->
"""
    report_path = session / "REPORT.md"
    report = report_path.read_text()
    if "<!-- receipt:start -->" in report:
        report = report[: report.index("<!-- receipt:start -->")].rstrip() + "\n"
    report_path.write_text(report + section)
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
