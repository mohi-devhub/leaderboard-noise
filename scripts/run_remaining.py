"""Prepare or execute the remaining models once, with server-side budget/queue control."""

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import time
import modal
from modal_connection import fresh_client, wait_existing_call
from run_pilot import command_json, shutdown, utc


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def download_results(session):
    resources = json.loads((session / "remaining-resources.json").read_text())
    volume_name = resources["volume_name"]
    if resources["owned_by"] != "evalnoise":
        raise ValueError("refusing to modify another project's volume")
    if (session / "remaining-volume-deleted.json").exists():
        result = json.loads((session / "remaining-job-result.json").read_text())
        for item in result.get("models", []):
            target = session / item["file"]
            if (
                not target.exists()
                or hashlib.sha256(target.read_bytes()).hexdigest() != item["sha256"]
            ):
                raise ValueError("verified local artifact changed after volume cleanup")
        return result
    with fresh_client() as client:
        volume = modal.Volume.from_name(volume_name, client=client)
        result_path = session / "remaining-job-result.json"
        if result_path.exists():
            result = json.loads(result_path.read_text())
        else:
            result = json.loads(b"".join(volume.read_file("manifest.json")))
            save(result_path, result)
        for item in result.get("models", []):
            name = item["file"]
            if Path(name).name != name or name == "Qwen2.5-1.5B-Instruct.json":
                raise ValueError("invalid artifact path or attempt to replace completed model")
            target = session / name
            if target.exists():
                if hashlib.sha256(target.read_bytes()).hexdigest() == item["sha256"]:
                    continue
                raise ValueError("existing result differs; never overwrite silently")
            partial = target.with_suffix(".json.partial")
            with partial.open("wb") as file:
                for chunk in volume.read_file(name):
                    file.write(chunk)
            if hashlib.sha256(partial.read_bytes()).hexdigest() != item["sha256"]:
                raise RuntimeError("artifact hash mismatch; retain volume")
            partial.replace(target)
        save(
            session / "remaining-download-receipt.json",
            {"verified_files": result.get("models", []), "at": utc()},
        )
        sidecar_hashes = {}
        for name in [
            "gpu-call.json",
            "gpu-started.json",
            "progress.json",
            "manifest.json",
            "runtime-fixes/tokenization/before.py",
            "runtime-fixes/tokenization/after.py",
            "runtime-fixes/tokenization/receipt.json",
        ]:
            try:
                data = b"".join(volume.read_file(name))
            except (FileNotFoundError, modal.exception.NotFoundError):
                continue
            target = session / "continuation-checkpoints" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            sidecar_hashes[name] = hashlib.sha256(data).hexdigest()
        save(session / "remaining-sidecar-receipt.json", {"sha256": sidecar_hashes})
        if result["status"] == "complete":
            modal.Volume.objects.delete(volume_name, client=client)
            save(
                session / "remaining-volume-deleted.json",
                {"volume_name": volume_name, "at": utc(), "all_artifacts_sha256_verified": True},
            )
    return result


def reconcile_stopped(session, record, ledger, ledger_path, original, result):
    record["ended_at"] = utc()
    shutdown(
        session / "remaining-shutdown.json",
        own_app_id=record["app_id"],
        stop_all=False,
    )
    record["status"] = (
        "remaining_stopped_needs_download" if result else "remaining_failed_needs_reconciliation"
    )
    apps = command_json("app", "list", "--json")
    save(session / "remaining-apps-final.json", apps)
    save(session / "remaining-containers-final.json", command_json("container", "list", "--json"))
    billing = command_json(
        "billing",
        "report",
        "--start",
        record["started_at"][:10],
        "--end",
        (datetime.now(timezone.utc) + timedelta(days=1)).date().isoformat(),
        "--resolution",
        "h",
        "--tag-names",
        "project,session",
        "--show-resources",
        "--json",
    )
    save(session / "remaining-billing-tagged.json", billing)
    own = next((a for a in apps if a["app_id"] == record["app_id"]))
    stop = datetime.fromisoformat(own["stopped_at"])
    gpu_calls = (
        command_json("function", "calls", record["gpu_function_id"], "--json")
        if record.get("gpu_function_id")
        else []
    )
    started_calls = [c for c in gpu_calls if c.get("started_at")]
    gpu_seconds = 0
    if started_calls:
        first = min(
            (datetime.fromisoformat(c["started_at"].replace("Z", "+00:00")) for c in started_calls)
        )
        gpu_seconds = max(0, (stop - first).total_seconds()) + 120
    cpu_seconds = max(0, (stop - datetime.fromisoformat(record["started_at"])).total_seconds()) + 60
    metered = sum((float(r["cost"]) for r in billing if r["object_id"] == record["app_id"]))
    record["estimated_spend_usd"] = max(
        (gpu_seconds * original["resource_ceiling_hourly_usd"] + cpu_seconds * 0.015825) / 3600
        + 0.015,
        metered,
    )
    record["reserved_usd"] = 0
    record["app_specific_metered_usage_usd"] = metered
    if record.get("gpu_function_id"):
        save(session / "remaining-gpu-calls.json", gpu_calls)
        save(
            session / "remaining-gpu-stats.json",
            command_json(
                "function",
                "stats",
                record["gpu_function_id"],
                "--since",
                record["started_at"],
                "--json",
            ),
        )
    save(ledger_path, ledger)


def finalize_local_wait(session, record, ledger, ledger_path, original, result):
    if result is not None:
        reconcile_stopped(session, record, ledger, ledger_path, original, result)
    else:
        record["status"] = "remaining_detached_running_or_needs_recovery"
        save(ledger_path, ledger)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("session", type=Path)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--submit-only", action="store_true")
    parser.add_argument("--download-only", action="store_true")
    args = parser.parse_args()
    session = args.session
    if args.download_only:
        download_results(session)
        return
    models = json.loads((session / "models.json").read_text())
    completed = []
    for model in models:
        file = session / (model["id"].rsplit("/", 1)[-1] + ".json")
        if file.exists() and json.loads(file.read_text())["status"] == "complete":
            completed.append(model["id"])
    remaining = [model for model in models if model["id"] not in completed]
    if len(completed) != 1 or len(remaining) != 5:
        raise RuntimeError(
            "this continuation is only for five unsubmitted models; never rerun completed work"
        )
    original = json.loads((session / "forecast.json").read_text())
    forecasts = [r for r in original["models"] if r["model"] not in completed]
    execution_limit = sum((f["execution_limit_seconds"] for f in forecasts)) + 900
    gpu_seconds_limit = execution_limit + 1800 + 2
    cpu_seconds_limit = gpu_seconds_limit + 1800
    resource_limit = (
        gpu_seconds_limit * original["resource_ceiling_hourly_usd"] + cpu_seconds_limit * 0.015825
    ) / 3600 + 0.15
    ledger_path = Path("results/budget-ledger.json")
    ledger = json.loads(ledger_path.read_text())
    spent = sum((e.get("estimated_spend_usd", 0) + e["reserved_usd"] for e in ledger["entries"]))
    approval_path = Path("experiments/remaining-approval.json")
    approval = (
        json.loads(approval_path.read_text()) if approval_path.exists() else {"approved": False}
    )
    forecast = {
        "created_at": utc(),
        "completed_models_preserved": completed,
        "remaining_models": [m["id"] for m in remaining],
        "prior_project_estimate_usd": spent,
        "forecast_job_usd": sum((f["forecast_usd"] for f in forecasts)) + 0.15,
        "conservative_job_usd": max(
            sum((f["reservation_usd"] for f in forecasts)) + 0.15, resource_limit
        ),
        "global_execution_limit_seconds": execution_limit,
        "resource_ceiling_includes_startup_and_queue_control": True,
        "project_cap_usd": 12,
        "requires_above_5_approval": True,
        "approval_present": approval.get("approved", False),
        "expected_gpu_family": "Modal A10",
        "cloud": "auto",
        "note": "One server-side CPU controller, one A10 job with per-model budget gates, and a temporary results volume. Stop within 30 minutes without A10 allocation. CPU/control/storage costs are covered by the $0.15 allowance; delete the volume only after all downloads verify.",
    }
    save(session / "remaining-forecast.json", forecast)
    print(json.dumps(forecast, indent=2), flush=True)
    if not args.execute:
        return
    if not approval.get("approved") or approval.get("session") != str(session):
        raise RuntimeError("user approval is required for the forecast over $5")
    if spent + forecast["conservative_job_usd"] > 12:
        raise RuntimeError("conservative continuation forecast crosses $12")
    if (session / "remaining-controller-handle.json").exists() or (
        session / "remaining-resources.json"
    ).exists():
        raise RuntimeError(
            "continuation already submitted; reconnect to its handle, never resubmit"
        )
    config = json.loads((session / "config.json").read_text())
    timeout = execution_limit
    if (
        datetime.fromisoformat(config["finish_before_utc"]) - datetime.now(timezone.utc)
    ).total_seconds() < timeout + 2700:
        raise RuntimeError("insufficient time before October 31")
    manifest = json.loads(Path("experiments/subset.json").read_text())
    frozen = Path("experiments/bfcl-items.jsonl")
    if hashlib.sha256(frozen.read_bytes()).hexdigest() != manifest["file_sha256"]:
        raise RuntimeError("frozen items changed")
    indices = {item: i for i, item in enumerate(manifest["full_ids"])}
    items = [
        {
            "item_id": r["item_id"],
            "messages": r["messages"],
            "messages_sha256": r["messages_sha256"],
            "seed_index": indices[r["item_id"]],
        }
        for r in map(json.loads, frozen.read_text().splitlines())
    ]
    import os
    from dotenv import load_dotenv

    load_dotenv(".env")
    token = (
        os.environ.get("HF_TOKEN")
        or (Path(os.environ.get("HF_HOME", str(Path.home() / ".cache/huggingface"))) / "token")
        .read_text()
        .strip()
    )
    secret = modal.Secret.from_dict({"HF_TOKEN": token})
    del token
    volume_name = "evalnoise-" + session.name + "-remaining"
    volume = modal.Volume.from_name(volume_name, create_if_missing=True)
    save(
        session / "remaining-resources.json",
        {"volume_name": volume_name, "owned_by": "evalnoise", "created_at": utc()},
    )
    image = (
        modal.Image.from_id("im-zY8KvpcqHk1j19XYHhLOTY")
        .add_local_file("scripts/gpu_worker.py", "/opt/gpu_worker.py", copy=True)
        .add_local_file("scripts/study_model_job.py", "/opt/study_model_job.py", copy=True)
        .run_commands(
            "python /opt/compiler_smoke.py --output /opt/compiler-preflight.json",
            "pip-audit --progress-spinner off --ignore-vuln PYSEC-2026-3447 --ignore-vuln GHSA-xmj3-9gf7-h52w --format json --output /opt/full-image-audit.json",
        )
    )
    app = modal.App(
        "evalnoise-study-remaining", tags={"project": "evalnoise", "session": session.name}
    )

    @app.function(
        image=image,
        gpu="A10",
        cpu=(2, 4),
        memory=(8192, 16384),
        volumes={"/artifacts": volume},
        secrets=[secret],
        max_containers=1,
        retries=0,
        timeout=timeout,
        startup_timeout=1800,
        scaledown_window=2,
        serialized=True,
        include_source=False,
    )
    def gpu_job(payload):
        import json
        import hashlib
        import os
        import sys
        import threading
        from datetime import datetime, timezone
        from pathlib import Path

        root = Path("/artifacts")
        start = time.monotonic()
        started = datetime.now(timezone.utc).isoformat()
        (root / "gpu-started.json").write_text(json.dumps({"started_at": started}))
        volume.commit()
        guard = threading.Timer(payload["timeout_seconds"], lambda: os._exit(124))
        guard.daemon = True
        guard.start()
        sys.path.insert(0, "/opt")
        from study_model_job import execute_model

        result = {"status": "running", "started_at": started, "models": []}
        try:
            import torch
            import subprocess

            gpu = torch.cuda.get_device_name()
            if gpu not in {"NVIDIA A10", "NVIDIA A10G"}:
                raise RuntimeError("allocated GPU is outside the authorized Modal A10 tier")
            uuid = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=uuid", "--format=csv,noheader"], text=True
            ).strip()
            result.update(
                gpu=gpu,
                gpu_uuid=uuid,
                cloud=os.environ.get("MODAL_CLOUD_PROVIDER"),
                region=os.environ.get("MODAL_REGION"),
            )
            for model, forecast_row in zip(payload["models"], payload["forecasts"], strict=True):
                total = (
                    payload["spent_before_usd"]
                    + 0.15
                    + (time.monotonic() - start + 120) * payload["combined_hourly_usd"] / 3600
                )
                if total + forecast_row["reservation_usd"] > 12:
                    result.update(status="budget_stop", error="next model would cross $12")
                    break
                print(
                    f"REMOTE_BUDGET_GATE {model['id']} total_estimate={total:.6f} next={forecast_row['reservation_usd']:.6f}",
                    flush=True,
                )
                task = {
                    "model": model,
                    "items": payload["items"],
                    "timing_item_ids": payload["timing_item_ids"],
                    "config": payload["config"],
                    "execution_limit_seconds": forecast_row["execution_limit_seconds"],
                    "expected_gpu_uuid": uuid,
                }
                value = execute_model(task)
                name = model["id"].rsplit("/", 1)[-1] + ".json"
                data = json.dumps(value).encode()
                (root / name).write_bytes(data)
                record = {
                    "model": model["id"],
                    "file": name,
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "status": value["status"],
                    "remote_seconds": value["remote_seconds"],
                    "forecast_seconds": forecast_row["forecast_seconds"],
                }
                result["models"].append(record)
                (root / "progress.json").write_text(json.dumps(result))
                volume.commit()
                print("REMOTE_MODEL_COMPLETE " + json.dumps(record), flush=True)
                if value["status"] != "complete":
                    result.update(status="failed", error=value.get("error", "worker failed"))
                    break
            else:
                result["status"] = "complete"
        except Exception as exc:
            result.update(status="failed", error_type=type(exc).__name__, error=str(exc))
        finally:
            guard.cancel()
        result["remote_seconds"] = time.monotonic() - start
        (root / "manifest.json").write_text(json.dumps(result))
        volume.commit()
        return result

    @app.function(
        image=image,
        cpu=(0.125, 0.25),
        memory=512,
        volumes={"/artifacts": volume},
        max_containers=1,
        retries=0,
        timeout=timeout + 1900,
        serialized=True,
        include_source=False,
    )
    def server_controller(payload):
        import json
        from pathlib import Path

        submitted = time.monotonic()
        call = gpu_job.spawn(payload)
        (Path("/artifacts") / "gpu-call.json").write_text(json.dumps({"call_id": call.object_id}))
        volume.commit()
        started = False
        while True:
            try:
                return call.get(timeout=15)
            except (modal.exception.FunctionTimeoutError, modal.exception.RemoteError):
                raise
            except TimeoutError:
                volume.reload()
                started = started or (Path("/artifacts") / "gpu-started.json").exists()
                if not started and time.monotonic() - submitted >= 1800:
                    call.cancel(terminate_containers=True)
                    return {
                        "status": "allocation_timeout",
                        "models": [],
                        "error": "no matching A10 allocation within 30 minutes",
                    }

    record = {
        "session": str(session),
        "started_at": utc(),
        "reserved_usd": forecast["conservative_job_usd"],
        "estimated_spend_usd": 0,
        "actual_invoice_usd": None,
        "status": "remaining_reserved",
        "volume_name": volume_name,
    }
    ledger["entries"].append(record)
    save(ledger_path, ledger)
    result = None
    try:
        with fresh_client() as client:
            with app.run(client=client, detach=True):
                record.update(
                    app_id=app.app_id,
                    gpu_function_id=gpu_job.object_id,
                    controller_function_id=server_controller.object_id,
                )
                save(ledger_path, ledger)
                payload = {
                    "models": remaining,
                    "forecasts": forecasts,
                    "items": items,
                    "timing_item_ids": manifest["pilot_ids"],
                    "config": config,
                    "timeout_seconds": timeout,
                    "spent_before_usd": spent,
                    "combined_hourly_usd": original["resource_ceiling_hourly_usd"] + 0.015825,
                }
                call = server_controller.spawn(payload)
                save(
                    session / "remaining-controller-handle.json",
                    {
                        "app_id": app.app_id,
                        "call_id": call.object_id,
                        "function_id": server_controller.object_id,
                        "gpu_function_id": gpu_job.object_id,
                        "volume_name": volume_name,
                    },
                )
                record["status"] = "remaining_running"
                save(ledger_path, ledger)
                if args.submit_only:
                    print("DETACHED_SUBMITTED " + call.object_id, flush=True)
                    return

                def reconnect(call_id, error_type):
                    path = session / "remaining-connection-recovery.json"
                    if path.exists():
                        raise RuntimeError("one reconnection exhausted")
                    save(path, {"call_id": call_id, "error_type": error_type, "at": utc()})

                result = wait_existing_call(call, timeout + 1900, reconnect)
                save(session / "remaining-job-result.json", result)
    finally:
        finalize_local_wait(session, record, ledger, ledger_path, original, result)
    if result is None:
        raise RuntimeError("no returned result; recover checkpoints, never resubmit")
    result = download_results(session)
    if result["status"] == "complete":
        record["status"] = "remaining_complete_ready_for_scoring"
        save(ledger_path, ledger)
    print("Continuation status: " + result["status"], flush=True)


if __name__ == "__main__":
    with modal.enable_output():
        main()
