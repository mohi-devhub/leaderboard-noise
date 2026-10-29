"""One detached, checkpointed L4 replication, bounded by follow-up and project caps."""

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import time

import modal

from modal_connection import fresh_client
from run_pilot import command_json, shutdown, utc


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def residency_seconds(calls, stopped, startup_seconds):
    if len(calls) > 1:
        raise RuntimeError("more than one call recorded; automatic job retries are forbidden")
    total = 0.0
    for call in calls:
        if not call.get("started_at"):
            continue
        start = datetime.fromisoformat(call["started_at"])
        elapsed = call.get("execution_time_seconds")
        end = (
            min(stopped, start + timedelta(seconds=elapsed + 2)) if elapsed is not None else stopped
        )
        observed_startup = call.get("startup_time_seconds")
        total += max(0, (end - start).total_seconds()) + (
            observed_startup if observed_startup is not None else startup_seconds
        )
    return total


def forecast(session, ledger):
    approval = json.loads((session / "approval.json").read_text())
    rate_path = session / "rates.json"
    if not rate_path.exists():
        rate_path = Path("results/metadata/modal-rates-l4-followup.json")
    rates = json.loads(rate_path.read_text())
    gpu_hourly = (
        float(rates["gpu_hour_cost_l4"])
        + 2 * float(rates["cpu_hour_cost"])
        + 16 * float(rates["mem_gib_hour_cost"])
    )
    controller_hourly = 3 * (
        0.25 * float(rates["cpu_hour_cost"]) + 0.5 * float(rates["mem_gib_hour_cost"])
    )
    combined = gpu_hourly + controller_hourly
    prior = sum(e.get("estimated_spend_usd", 0) + e["reserved_usd"] for e in ledger["entries"])
    followup_root = approval.get("followup_root", str(session))
    followup_prior = sum(
        e.get("estimated_spend_usd", 0) + e["reserved_usd"]
        for e in ledger["entries"]
        if e.get("followup_root", e["session"]) == followup_root
    )
    available = min(approval["followup_cap_usd"] - followup_prior, ledger["cap_usd"] - prior)
    models = json.loads((session / "models.json").read_text())
    rows = []
    for model in models:
        job = json.loads(
            (Path(approval["a10_session"]) / (model["id"].rsplit("/", 1)[-1] + ".json")).read_text()
        )
        baseline = 60.0
        for arm in job["arms"][:2]:
            meta = arm["metadata"]
            baseline += meta["startup_seconds"] + meta["smoke_seconds"]
            baseline += sum(
                t["elapsed_seconds"] + t["warmup_seconds"]
                for t in meta["timings"]
                if t["phase"] == "evaluation" and t["run_id"] != "sampling"
            )
        rows.append(
            {
                "model": model["id"],
                "a10_greedy_startup_warmup_seconds_plus_60": baseline,
                "forecast_seconds": baseline * 1.7,
                "execution_limit_seconds": math.ceil(baseline * 2),
            }
        )
    timeout = sum(r["execution_limit_seconds"] for r in rows) + 120
    bound = (
        (timeout + 1800 + 300 + 120) * gpu_hourly + (timeout + 1800 + 120 + 60) * controller_hourly
    ) / 3600 + 0.15
    result = {
        "created_at": utc(),
        "models": rows,
        "planned_predictions": len(models) * 500 * 3 * 2,
        "gpu": "L4",
        "prior_project_estimate_usd": prior,
        "prior_followup_estimate_usd": followup_prior,
        "followup_root": followup_root,
        "followup_cap_usd": approval["followup_cap_usd"],
        "project_cap_usd": ledger["cap_usd"],
        "effective_followup_cap_usd": available,
        "forecast_usd": (
            (sum(r["forecast_seconds"] for r in rows) + 120) * gpu_hourly
            + (sum(r["forecast_seconds"] for r in rows) + 1800 + 120 + 60) * controller_hourly
        )
        / 3600
        + 0.15,
        "conservative_bound_usd": bound,
        "gpu_resource_hourly_usd": gpu_hourly,
        "controller_resource_hourly_usd": controller_hourly,
        "combined_resource_hourly_usd": combined,
        "execution_limit_seconds": timeout,
        "gpu_startup_limit_seconds": 300,
        "allocation_limit_seconds": 1800,
        "allocation_billed_gpu_allowance_seconds": 1800,
        "preemption_restart_gpu_allowance_seconds": 300,
        "controller_nonpreemptible": True,
        "controller_cpu_memory_price_multiplier": 3,
        "stop_and_accounting_buffer_seconds": 120,
        "non_gpu_allowance_usd": 0.15,
        "forecast_time_multiplier_assumption": 1.7,
        "bounded_time_multiplier": 2,
        "note": "L4 time multipliers are planning assumptions, not measured speed ratios. Two CPU cores are both requested and capped; RAM remains capped at 16 GiB. Generation settings and all 500 items match A10. Greedy only; no additional stochastic or throughput trials.",
    }
    save(session / "forecast.json", result)
    if not approval["approved"] or approval["session"] != str(session):
        raise RuntimeError("follow-up authorization does not match this session")
    if bound > available:
        raise RuntimeError("bounded forecast exceeds follow-up or original project cap")
    return result


def submit(session):
    if (session / "resources.json").exists() or (session / "controller-handle.json").exists():
        raise RuntimeError(
            "submission already attempted; recover the existing call, never resubmit"
        )
    ledger_path = Path("results/budget-ledger.json")
    ledger = json.loads(ledger_path.read_text())
    plan = forecast(session, ledger)
    config = json.loads((session / "config.json").read_text())
    models = json.loads((session / "models.json").read_text())
    if (
        datetime.fromisoformat(config["finish_before_utc"]) - datetime.now(timezone.utc)
    ).total_seconds() < plan["execution_limit_seconds"] + 2400:
        raise RuntimeError("insufficient time before the October 31 deadline")
    subset = json.loads(Path("experiments/subset.json").read_text())
    source = Path("experiments/bfcl-items.jsonl")
    if hashlib.sha256(source.read_bytes()).hexdigest() != subset["file_sha256"]:
        raise RuntimeError("frozen items changed")
    indices = {item: i for i, item in enumerate(subset["full_ids"])}
    items = [
        {
            "item_id": r["item_id"],
            "messages": r["messages"],
            "messages_sha256": r["messages_sha256"],
            "seed_index": indices[r["item_id"]],
        }
        for r in map(json.loads, source.read_text().splitlines())
    ]
    approval = json.loads((session / "approval.json").read_text())
    if approval.get("resume_from"):
        previous_path = Path(approval["resume_from"]) / "collection-result.json"
        if not previous_path.exists():
            previous_path = Path(approval["resume_from"]) / "job-result.json"
        previous = json.loads(previous_path.read_text())
        completed = {r["model"] for r in previous["models"] if r["status"] == "complete"}
        requested = {name for pair in approval["pairs"] for name in pair}
        if {m["id"] for m in models} != requested - completed:
            raise RuntimeError("continuation must contain exactly the unfinished requested models")
    elif len(models) != 4:
        raise RuntimeError("the initial follow-up requires exactly four models")
    if len(items) != 500:
        raise RuntimeError("the authorized follow-up requires all 500 frozen items")
    from dotenv import load_dotenv

    load_dotenv(".env")
    token_path = Path(os.environ.get("HF_HOME", str(Path.home() / ".cache/huggingface"))) / "token"
    token = os.environ.get("HF_TOKEN") or token_path.read_text().strip()
    secret = modal.Secret.from_dict({"HF_TOKEN": token})
    del token
    volume_name = "evalnoise-" + session.name
    volume = modal.Volume.from_name(volume_name, create_if_missing=True)
    save(session / "resources.json", {"owned_by": "evalnoise", "volume_name": volume_name})
    image = (
        modal.Image.from_id("im-zY8KvpcqHk1j19XYHhLOTY")
        .add_local_file("scripts/gpu_worker.py", "/opt/gpu_worker.py", copy=True)
        .add_local_file("scripts/study_model_job.py", "/opt/study_model_job.py", copy=True)
        .add_local_file("scripts/followup_state.py", "/opt/followup_state.py", copy=True)
        .env({"EVALNOISE_SESSION": session.name})
        .run_commands(
            "python /opt/compiler_smoke.py --output /opt/compiler-preflight.json",
            "pip-audit --progress-spinner off --ignore-vuln PYSEC-2026-3447 --ignore-vuln GHSA-xmj3-9gf7-h52w --format json --output /opt/full-image-audit.json",
        )
    )
    app = modal.App("evalnoise-l4-followup", tags={"project": "evalnoise", "session": session.name})
    timeout = plan["execution_limit_seconds"]

    @app.function(
        image=image,
        gpu="L4",
        cpu=(2, 2),
        memory=(8192, 16384),
        volumes={"/artifacts": volume},
        secrets=[secret],
        max_containers=1,
        retries=0,
        timeout=timeout,
        startup_timeout=300,
        scaledown_window=2,
        serialized=True,
        include_source=False,
    )
    def gpu_job(payload):
        import hashlib
        import json
        import os
        from datetime import datetime, timezone
        from pathlib import Path
        import subprocess
        import sys
        import threading
        import time

        def now():
            return datetime.now(timezone.utc).isoformat()

        root = Path("/artifacts")
        start = time.monotonic()
        sys.path.insert(0, "/opt")
        from followup_state import begin_once

        claim = {
            "session": payload["session"],
            "started_at": now(),
            "execution_limit_seconds": payload["plan"]["execution_limit_seconds"],
        }
        previous = begin_once(root, claim)
        if previous is not None:
            (root / "manifest.json").write_text(json.dumps(previous))
            volume.commit()
            return previous
        volume.commit()
        (root / "gpu-started.json").write_text(json.dumps({"started_at": now()}))
        volume.commit()
        guard = threading.Timer(payload["plan"]["execution_limit_seconds"], lambda: os._exit(124))
        guard.daemon = True
        guard.start()
        from study_model_job import execute_model

        result = {"status": "running", "started_at": now(), "models": [], "budget_checks": []}
        try:
            import torch

            if torch.cuda.get_device_name() != "NVIDIA L4":
                raise RuntimeError("only NVIDIA L4 is authorized; no GPU fallback")
            uuid = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=uuid", "--format=csv,noheader"], text=True
            ).strip()
            result.update(
                gpu="NVIDIA L4",
                gpu_uuid=uuid,
                cloud=os.environ.get("MODAL_CLOUD_PROVIDER"),
                region=os.environ.get("MODAL_REGION"),
            )
            for model, row in zip(payload["models"], payload["plan"]["models"], strict=True):
                plan = payload["plan"]
                through_next = time.monotonic() - start + row["execution_limit_seconds"]
                projected = (
                    plan["non_gpu_allowance_usd"]
                    + (
                        (through_next + 1800 + 300 + 120) * plan["gpu_resource_hourly_usd"]
                        + (through_next + 1800 + 120 + 60) * plan["controller_resource_hourly_usd"]
                    )
                    / 3600
                )
                check = {
                    "model": model["id"],
                    "projected_followup_bound_after_next_model_usd": projected,
                    "followup_effective_cap_usd": plan["effective_followup_cap_usd"],
                }
                result["budget_checks"].append(check)
                (root / "progress.json").write_text(json.dumps(result))
                volume.commit()
                if projected > plan["effective_followup_cap_usd"]:
                    result.update(status="budget_stop", error="next model would cross a cap")
                    break
                task = {
                    "model": model,
                    "items": payload["items"],
                    "config": payload["config"],
                    "execution_limit_seconds": row["execution_limit_seconds"],
                    "expected_gpu_uuid": uuid,
                    "gpu_family": "L4",
                    "include_sampling": False,
                    "collect_timing": False,
                }
                value = execute_model(task)
                name = model["id"].rsplit("/", 1)[-1] + ".json"
                content = json.dumps(value).encode()
                (root / name).write_bytes(content)
                result["models"].append(
                    {
                        "model": model["id"],
                        "file": name,
                        "sha256": hashlib.sha256(content).hexdigest(),
                        "status": value["status"],
                        "remote_seconds": value["remote_seconds"],
                    }
                )
                (root / "progress.json").write_text(json.dumps(result))
                volume.commit()
                print("L4_CHECKPOINT " + model["id"], flush=True)
                if value["status"] != "complete":
                    result.update(status="failed", error=value.get("error", "model failed"))
                    break
            else:
                result["status"] = "complete"
        except Exception as exc:
            result.update(status="failed", error_type=type(exc).__name__, error=str(exc))
        finally:
            guard.cancel()
        result.update(ended_at=now(), remote_seconds=time.monotonic() - start)
        (root / "manifest.json").write_text(json.dumps(result))
        volume.commit()
        return result

    @app.function(
        image=image,
        cpu=(0.125, 0.25),
        memory=(256, 512),
        nonpreemptible=True,
        volumes={"/artifacts": volume},
        max_containers=1,
        retries=0,
        timeout=timeout + 1860,
        serialized=True,
        include_source=False,
    )
    def controller(payload):
        import json
        from datetime import datetime, timezone
        from pathlib import Path

        root = Path("/artifacts")
        start = time.monotonic()
        volume.reload()
        handle = root / "gpu-call.json"
        if handle.exists():
            saved = json.loads(handle.read_text())
            if saved["function_id"] != gpu_job.object_id:
                raise RuntimeError("saved GPU call belongs to another function")
            call = modal.FunctionCall.from_id(saved["call_id"])
        else:
            call = gpu_job.spawn(payload)
            handle.write_text(
                json.dumps({"call_id": call.object_id, "function_id": gpu_job.object_id})
            )
            volume.commit()
        missing_workers = 0

        def stopped_result(status, error):
            volume.reload()
            path = root / "progress.json"
            value = json.loads(path.read_text()) if path.exists() else {"models": []}
            value.update(
                status=status, error=error, ended_at=datetime.now(timezone.utc).isoformat()
            )
            (root / "manifest.json").write_text(json.dumps(value))
            volume.commit()
            return value

        while True:
            try:
                return call.get(timeout=15)
            except (modal.exception.FunctionTimeoutError, modal.exception.RemoteError) as exc:
                return stopped_result("failed", type(exc).__name__)
            except TimeoutError:
                volume.reload()
                if (
                    not (Path("/artifacts") / "gpu-started.json").exists()
                    and time.monotonic() - start >= 1800
                ):
                    call.cancel(terminate_containers=True)
                    return stopped_result("allocation_timeout", "no L4 within 30 minutes")
                claim_path = root / "execution-claim.json"
                if claim_path.exists():
                    claim = json.loads(claim_path.read_text())
                    elapsed = (
                        datetime.now(timezone.utc) - datetime.fromisoformat(claim["started_at"])
                    ).total_seconds()
                    if elapsed > payload["plan"]["execution_limit_seconds"] + 30:
                        call.cancel(terminate_containers=True)
                        return stopped_result("budget_timeout", "absolute execution window expired")
                    try:
                        stats = gpu_job.get_current_stats()
                        absent = stats.num_total_runners == 0 and stats.backlog > 0
                        missing_workers = missing_workers + 1 if absent else 0
                    except (modal.exception.ConnectionError, modal.exception.ServiceError):
                        missing_workers = 0
                    if missing_workers >= 2:
                        cutoff = datetime.now(timezone.utc).isoformat()
                        call.cancel(terminate_containers=True)
                        (root / "preemption.json").write_text(
                            json.dumps(
                                {
                                    "gpu_terminated_at_utc": cutoff,
                                    "termination_time_is_upper_bound": True,
                                    "evidence": "two consecutive zero-runner, positive-backlog snapshots after an execution claim",
                                }
                            )
                        )
                        volume.commit()
                        return stopped_result(
                            "preempted", "GPU worker disappeared; replay cancelled"
                        )

    record = {
        "session": str(session),
        "started_at": utc(),
        "status": "l4_followup_reserved",
        "estimated_spend_usd": 0,
        "reserved_usd": plan["conservative_bound_usd"],
        "actual_invoice_usd": None,
        "followup_root": plan["followup_root"],
    }
    ledger["entries"].append(record)
    save(ledger_path, ledger)
    with fresh_client() as client:
        with app.run(client=client, detach=True):
            record.update(
                app_id=app.app_id,
                gpu_function_id=gpu_job.object_id,
                controller_function_id=controller.object_id,
            )
            save(ledger_path, ledger)
            call = controller.spawn(
                {
                    "models": models,
                    "items": items,
                    "config": config,
                    "plan": plan,
                    "session": str(session),
                }
            )
            save(session / "controller-handle.json", dict(record, call_id=call.object_id))
            record["status"] = "l4_followup_detached_running"
            save(ledger_path, ledger)
            print("L4_DETACHED_SUBMITTED " + call.object_id, flush=True)


def observe(session):
    handle = json.loads((session / "controller-handle.json").read_text())
    resources = json.loads((session / "resources.json").read_text())
    expected_models = len(json.loads((session / "models.json").read_text()))
    if resources["owned_by"] != "evalnoise":
        raise RuntimeError("refusing another project's resources")
    result = (
        json.loads((session / "job-result.json").read_text())
        if (session / "job-result.json").exists()
        else None
    )
    previous = None
    while result is None:
        try:
            with fresh_client() as client:
                volume = modal.Volume.from_name(resources["volume_name"], client=client)
                try:
                    result = json.loads(b"".join(volume.read_file("manifest.json")))
                except (FileNotFoundError, modal.exception.NotFoundError):
                    try:
                        progress = json.loads(b"".join(volume.read_file("progress.json")))
                    except (FileNotFoundError, modal.exception.NotFoundError):
                        progress = {"status": "queued_or_initializing", "models": []}
                    save(session / "progress.json", progress)
                    current = len(progress["models"])
                    if current != previous:
                        print(f"L4_VERIFIED_PROGRESS {current}/{expected_models}", flush=True)
                        previous = current
                    gpu_handle_path = session / "gpu-call.json"
                    try:
                        saved_gpu = json.loads(b"".join(volume.read_file("gpu-call.json")))
                        save(gpu_handle_path, saved_gpu)
                    except (FileNotFoundError, modal.exception.NotFoundError):
                        saved_gpu = (
                            json.loads(gpu_handle_path.read_text())
                            if gpu_handle_path.exists()
                            else None
                        )
                    observed_call_id = saved_gpu["call_id"] if saved_gpu else handle["call_id"]
                    try:
                        result = modal.FunctionCall.from_id(observed_call_id, client=client).get(
                            timeout=0
                        )
                    except (
                        modal.exception.FunctionTimeoutError,
                        modal.exception.RemoteError,
                    ) as exc:
                        result = dict(progress, status="failed", error_type=type(exc).__name__)
                    except TimeoutError:
                        pass
                try:
                    save(
                        session / "gpu-call.json",
                        json.loads(b"".join(volume.read_file("gpu-call.json"))),
                    )
                except (FileNotFoundError, modal.exception.NotFoundError):
                    pass
        except (modal.exception.ServiceError, modal.exception.ConnectionError) as exc:
            recovery = session / "observer-reconnection.json"
            if recovery.exists():
                raise
            save(
                recovery, {"at": utc(), "error_type": type(exc).__name__, "job_resubmitted": False}
            )
            print("L4_OBSERVER_RECONNECT_EXISTING_CALL", flush=True)
        if result is None:
            time.sleep(30)
    save(session / "job-result.json", result)
    shutdown(session / "shutdown.json", own_app_id=handle["app_id"], stop_all=False)
    ledger_path = Path("results/budget-ledger.json")
    ledger = json.loads(ledger_path.read_text())
    record = next(e for e in ledger["entries"] if e.get("app_id") == handle["app_id"])
    plan = json.loads((session / "forecast.json").read_text())
    apps = command_json("app", "list", "--json")
    containers = command_json("container", "list", "--json")
    own = next(a for a in apps if a["app_id"] == handle["app_id"])
    stopped = datetime.fromisoformat(own["stopped_at"])
    calls = command_json("function", "calls", handle["gpu_function_id"], "--json")
    save(session / "gpu-calls.json", calls)
    save(session / "apps-final.json", apps)
    save(session / "containers-final.json", containers)
    cpu_calls = command_json("function", "calls", handle["controller_function_id"], "--json")
    save(session / "controller-calls.json", cpu_calls)
    gpu_seconds = residency_seconds(calls, stopped, 300)
    cpu_seconds = residency_seconds(cpu_calls, stopped, 60)
    estimate = (
        gpu_seconds * plan["gpu_resource_hourly_usd"]
        + cpu_seconds * plan["controller_resource_hourly_usd"]
    ) / 3600 + plan["non_gpu_allowance_usd"]
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
    save(session / "billing-tagged.json", billing)
    metered = sum(float(r["cost"]) for r in billing if r["object_id"] == handle["app_id"])
    record.update(
        status="l4_followup_stopped_" + result["status"],
        ended_at=utc(),
        reserved_usd=0,
        estimated_spend_usd=max(estimate, metered),
        app_specific_metered_usage_usd=metered,
    )
    save(ledger_path, ledger)
    with fresh_client() as client:
        volume = modal.Volume.from_name(resources["volume_name"], client=client)
        for row in result["models"]:
            target = session / row["file"]
            if Path(row["file"]).name != row["file"]:
                raise ValueError("invalid artifact path")
            if not target.exists():
                temporary = target.with_suffix(".json.partial")
                with temporary.open("wb") as file:
                    for block in volume.read_file(row["file"]):
                        file.write(block)
                if hashlib.sha256(temporary.read_bytes()).hexdigest() != row["sha256"]:
                    raise RuntimeError("download hash mismatch; keep the volume")
                temporary.replace(target)
            elif hashlib.sha256(target.read_bytes()).hexdigest() != row["sha256"]:
                raise RuntimeError("refusing to overwrite different saved results")
        save(session / "download-receipt.json", {"verified": result["models"], "at": utc()})
        for sidecar in (
            "execution-claim.json",
            "preemption.json",
            "gpu-started.json",
            "progress.json",
        ):
            try:
                content = b"".join(volume.read_file(sidecar))
            except (FileNotFoundError, modal.exception.NotFoundError):
                continue
            (session / ("remote-" + sidecar)).write_bytes(content)
            if sidecar == "preemption.json":
                (session / sidecar).write_bytes(content)
        if result["status"] == "complete" and not (session / "volume-deleted.json").exists():
            modal.Volume.objects.delete(resources["volume_name"], client=client)
            save(session / "volume-deleted.json", {"at": utc(), "sha256_verified": True})
    save(
        session / "receipt.json",
        {
            "checked_at": utc(),
            "forecast_usd": plan["forecast_usd"],
            "conservative_bound_usd": plan["conservative_bound_usd"],
            "estimated_spend_usd": record["estimated_spend_usd"],
            "app_specific_gross_metered_usage_usd": metered,
            "project_estimate_usd": sum(e["estimated_spend_usd"] for e in ledger["entries"]),
            "active_reservations_usd": sum(e["reserved_usd"] for e in ledger["entries"]),
            "actual_invoice_usd": None,
            "metering_provisional": True,
            "own_apps_stopped": own["state"] == "stopped",
            "own_running_containers": sum(c["app_id"] == handle["app_id"] for c in containers),
            "other_project_modified": False,
        },
    )
    print("L4_DOWNLOADED " + result["status"], flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("session", type=Path)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--execute", action="store_true")
    action.add_argument("--observe", action="store_true")
    args = parser.parse_args()
    if args.execute:
        submit(args.session)
    elif args.observe:
        observe(args.session)
    else:
        ledger = json.loads(Path("results/budget-ledger.json").read_text())
        print(json.dumps(forecast(args.session, ledger), indent=2))


if __name__ == "__main__":
    with modal.enable_output():
        main()
