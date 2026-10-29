"""Replace reserved startup/setup allowances with stopped-call accounting evidence."""

from datetime import datetime
import json
from pathlib import Path

from run_l4_followup import residency_seconds, save
from run_pilot import utc


def refresh_receipt(session):
    receipt_path = session / "receipt.json"
    receipt = json.loads(receipt_path.read_text())
    if not receipt["own_apps_stopped"] or receipt["own_running_containers"]:
        raise RuntimeError("accounting refinement requires confirmed shutdown")
    handle = json.loads((session / "controller-handle.json").read_text())
    apps = json.loads((session / "apps-final.json").read_text())
    own = next(a for a in apps if a["app_id"] == handle["app_id"])
    stopped = datetime.fromisoformat(own["stopped_at"])
    calls = json.loads((session / "gpu-calls.json").read_text())
    cpu_calls = json.loads((session / "controller-calls.json").read_text())
    plan = json.loads((session / "forecast.json").read_text())
    gpu_stopped = stopped
    preemption_path = session / "preemption.json"
    if preemption_path.exists():
        preemption = json.loads(preemption_path.read_text())
        gpu_stopped = min(stopped, datetime.fromisoformat(preemption["gpu_terminated_at_utc"]))
    gpu_seconds = residency_seconds(calls, gpu_stopped, 300)
    cpu_seconds = residency_seconds(cpu_calls, stopped, 60)
    resource_estimate = (
        gpu_seconds * plan["gpu_resource_hourly_usd"]
        + cpu_seconds * plan["controller_resource_hourly_usd"]
    ) / 3600 + 0.015
    # The $0.15 planning allowance is not a measured charge. Keep it in forecast.json.
    estimate = max(resource_estimate, receipt["app_specific_gross_metered_usage_usd"])
    ledger_path = Path("results/budget-ledger.json")
    ledger = json.loads(ledger_path.read_text())
    entry = next(e for e in ledger["entries"] if e.get("app_id") == handle["app_id"])
    entry.update(
        estimated_spend_usd=estimate,
        estimate_basis="larger of app-specific gross metering and stopped-call resource ceiling using observed startup when available, configured fallback otherwise, plus $0.015 setup/egress margin; client waiting excluded",
        reserved_usd=0,
        initial_reserved_usd=plan["conservative_bound_usd"],
        released_reservation_usd=plan["conservative_bound_usd"],
        unused_allowance_usd=max(0, plan["conservative_bound_usd"] - estimate),
    )
    save(ledger_path, ledger)
    archive = session / "receipt-initial-resource-bound.json"
    if not archive.exists():
        archive.write_bytes(receipt_path.read_bytes())
    receipt.update(
        checked_at=utc(),
        estimated_spend_usd=estimate,
        timed_resource_estimate_usd=resource_estimate,
        gpu_residency_seconds_including_startup_estimate=gpu_seconds,
        controller_residency_seconds_including_startup_estimate=cpu_seconds,
        startup_fallback_used=any(
            c.get("started_at") and c.get("startup_time_seconds") is None for c in calls + cpu_calls
        ),
        gpu_runtime_cutoff_utc=gpu_stopped.isoformat(),
        setup_egress_margin_usd=0.015,
        project_estimate_usd=sum(e["estimated_spend_usd"] for e in ledger["entries"]),
        active_reservations_usd=sum(e["reserved_usd"] for e in ledger["entries"]),
    )
    if receipt["estimated_spend_usd"] > 5 or receipt["project_estimate_usd"] > 12:
        raise RuntimeError("recorded usage crosses a cap; report explicitly")
    save(receipt_path, receipt)
    return receipt
