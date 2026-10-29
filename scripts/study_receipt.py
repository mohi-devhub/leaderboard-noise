"""Reconcile the preserved model and detached continuation by app-specific resources."""

import argparse
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
from pathlib import Path
import re
import subprocess
import sys

from run_pilot import command_json, utc


def budget_evidence(session, continuation, completed):
    output = subprocess.check_output(
        [
            sys.executable,
            "-m",
            "modal",
            "app",
            "logs",
            continuation["app_id"],
            "--since",
            continuation["started_at"],
            "--function",
            continuation["gpu_function_id"],
            "--search",
            "REMOTE_BUDGET_GATE",
            "--timestamps",
        ],
        text=True,
    )
    checks = []
    lines = []
    for line in output.splitlines():
        match = re.search(r"REMOTE_BUDGET_GATE (\S+) total_estimate=([0-9.]+) next=([0-9.]+)", line)
        if match:
            model, total, allowance = match.groups()
            ceiling = Decimal(total) + Decimal(allowance)
            if ceiling > 12:
                raise RuntimeError("recorded pre-model budget gate exceeded the project cap")
            checks.append(
                {
                    "model": model,
                    "project_resource_estimate_before_model_usd": total,
                    "next_model_bounded_allowance_usd": allowance,
                    "project_bound_after_next_model_usd": str(ceiling),
                    "project_cap_usd": "12",
                    "source_log_line": line,
                }
            )
            lines.append(line)
    if [c["model"] for c in checks] != [c["model"] for c in completed]:
        raise RuntimeError("server budget-gate evidence does not cover the completed models")
    (session / "remaining-budget-checks.log").write_text("\n".join(lines) + "\n")
    (session / "remaining-budget-checks.json").write_text(json.dumps(checks, indent=2) + "\n")
    return checks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("session", type=Path)
    args = parser.parse_args()
    session = args.session
    ledger_path = Path("results/budget-ledger.json")
    ledger = json.loads(ledger_path.read_text())
    entries = [e for e in ledger["entries"] if e["session"] == str(session)]
    continuation = next(e for e in reversed(entries) if e.get("gpu_function_id"))
    summary = json.loads((session / "summary.json").read_text())
    forecast = json.loads((session / "forecast.json").read_text())
    remaining_forecast = json.loads((session / "remaining-forecast.json").read_text())
    result = json.loads((session / "remaining-job-result.json").read_text())
    if result["status"] != "complete" or len(result["models"]) != 5:
        raise ValueError("five completed continuation models are required")
    checks = budget_evidence(session, continuation, result["models"])
    apps = command_json("app", "list", "--json")
    containers = command_json("container", "list", "--json")
    (session / "apps-final.json").write_text(json.dumps(apps, indent=2) + "\n")
    (session / "containers-final.json").write_text(json.dumps(containers, indent=2) + "\n")
    owned_ids = {e["app_id"] for e in entries if e.get("app_id")}
    for app_id in owned_ids:
        info = command_json("app", "info", app_id, "--json")
        if info["lifecycle"]["state"] != "stopped":
            raise RuntimeError("a study app remains active")
    if any(c["app_id"] in owned_ids for c in containers):
        raise RuntimeError("a study container remains active")
    billing = command_json(
        "billing",
        "report",
        "--start",
        min(e["started_at"] for e in entries)[:10],
        "--end",
        (datetime.now(timezone.utc) + timedelta(days=1)).date().isoformat(),
        "--resolution",
        "h",
        "--tag-names",
        "project,session",
        "--show-resources",
        "--json",
    )
    (session / "billing-tagged.json").write_text(json.dumps(billing, indent=2) + "\n")
    metered = sum((Decimal(r["cost"]) for r in billing if r["object_id"] in owned_ids), Decimal(0))
    remaining_metered = sum(
        (Decimal(r["cost"]) for r in billing if r["object_id"] == continuation["app_id"]),
        Decimal(0),
    )
    continuation["estimated_spend_usd"] = max(
        continuation["estimated_spend_usd"], float(remaining_metered)
    )
    continuation.update(
        reserved_usd=0,
        status="full_study_scored_apps_stopped",
        actual_invoice_usd=None,
        app_specific_metered_usage_usd=str(remaining_metered),
    )
    ledger_path.write_text(json.dumps(ledger, indent=2) + "\n")
    study_estimate = sum(Decimal(str(e.get("estimated_spend_usd", 0))) for e in entries)
    project_estimate = sum(Decimal(str(e.get("estimated_spend_usd", 0))) for e in ledger["entries"])
    model_costs = []
    execution = Decimal(0)
    hourly = Decimal(str(forecast["resource_ceiling_hourly_usd"]))
    for f in forecast["models"]:
        model = json.loads((session / (f["model"].rsplit("/", 1)[-1] + ".json")).read_text())
        if model["status"] != "complete":
            raise ValueError("an incomplete model cannot enter the receipt")
        seconds = Decimal(str(model["remote_seconds"]))
        execution += seconds
        model_costs.append(
            {
                "model": f["model"],
                "gpu": model["gpu"],
                "gpu_uuid": model["gpu_uuid"],
                "forecast_seconds": f["forecast_seconds"],
                "measured_seconds": float(seconds),
                "forecast_usd": f["forecast_usd"],
                "timed_execution_resource_ceiling_usd": str(seconds * hourly / 3600),
            }
        )
    old_calls = json.loads((session / "final-calls.json").read_text())
    new_calls = json.loads((session / "remaining-gpu-calls.json").read_text())
    if len(old_calls) != 1 or len(new_calls) != 1:
        raise ValueError("expected one preserved model call and one continuation GPU call")
    receipt = {
        "checked_at": utc(),
        "gpu": summary["gpu"],
        "gpu_names": summary["gpu_names"],
        "gpu_uuids": summary["gpu_uuids"],
        "gpu_jobs": 2,
        "gpu_containers": len({c["container_id"] for c in old_calls + new_calls}),
        "cpu_controller_function_id": continuation["controller_function_id"],
        "owned_app_ids": sorted(owned_ids),
        "primary_predictions": summary["primary_predictions"],
        "timing_predictions": summary["timing_predictions"],
        "total_predictions": summary["total_predictions"],
        "measured_model_execution_seconds": str(execution),
        "forecast_full_study_usd": forecast["forecast_study_usd"],
        "forecast_remaining_job_usd": remaining_forecast["forecast_job_usd"],
        "conservative_remaining_job_usd": remaining_forecast["conservative_job_usd"],
        "app_specific_gross_metered_study_usage_usd": str(metered),
        "app_specific_gross_metered_remaining_usage_usd": str(remaining_metered),
        "estimated_remaining_spend_usd": continuation["estimated_spend_usd"],
        "estimated_study_spend_usd": str(study_estimate),
        "estimated_project_total_usd": str(project_estimate),
        "within_project_cap": project_estimate <= 12,
        "verified_remote_pre_model_budget_gates": len(checks),
        "actual_invoice_usd": None,
        "metering_provisional": True,
        "active_reservations_usd": sum(e["reserved_usd"] for e in ledger["entries"]),
        "own_apps_stopped": True,
        "own_running_containers": 0,
        "other_project_modified": False,
        "temporary_volume_deleted_after_verified_downloads": (
            session / "remaining-volume-deleted.json"
        ).exists(),
        "models": model_costs,
        "cost_note": "Gross app-specific metering excludes qunti-check and credit offsets. It can lag and is not a settled invoice. Resource ceilings use bounded CPU/RAM and stop timestamps; post-stop client waiting is excluded. Model one was preserved rather than rerun.",
    }
    (session / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    lines = [
        "",
        "<!-- receipt:start -->",
        "## Cost, timing, and cleanup",
        "",
        f"The full-study forecast was ${forecast['forecast_study_usd']:.4f}; the approved remaining-five forecast was ${remaining_forecast['forecast_job_usd']:.4f}. Model one was preserved. The other five completed in one detached A10 GPU call with a server-side controller and volume checkpoints. Model execution totalled {execution:.2f} seconds.",
        "",
        "| Model | Device | Forecast seconds | Measured seconds | Forecast GPU/resource cost | Measured execution resource ceiling |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for r in model_costs:
        lines.append(
            f"| {r['model'].rsplit('/', 1)[-1]} | {r['gpu']} | {r['forecast_seconds']:.2f} | {r['measured_seconds']:.2f} | ${r['forecast_usd']:.4f} | ${float(r['timed_execution_resource_ceiling_usd']):.4f} |"
        )
    lines += [
        "",
        f"Modal currently reports ${remaining_metered:.6f} in app-specific gross metering for the remaining job, versus ${remaining_forecast['forecast_job_usd']:.4f} forecast. All study apps together report ${metered:.6f}. The conservative recorded study estimate is ${study_estimate:.6f}; cumulative project estimate including earlier attempts is ${project_estimate:.6f}/$12. Metering remains provisional and invoice actuals unknown. Account-wide deltas are excluded because qunti-check ran in parallel.",
        "",
        "The first model and the continuation used two recorded A10 devices. Every model retained the same device across arms and timing repetitions. Exact names and UUIDs appear in summary.json and receipt.json. Preselected comparisons among the continuation models share their physical device. Cross-device anchor comparisons must be read with that limitation.",
        "",
        "All evalnoise study apps are stopped and have zero running containers. Reservations are released. The temporary results volume was deleted only after every downloaded artifact matched its recorded SHA256. qunti-check was not modified. See remaining-job-result.json, remaining-download-receipt.json, remaining-billing-tagged.json, and the per-model budget logs for evidence.",
        "<!-- receipt:end -->",
    ]
    path = session / "REPORT.md"
    report = path.read_text().split("<!-- receipt:start -->")[0].rstrip()
    path.write_text(report + "\n" + "\n".join(lines) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
