"""A10-only study, one bounded model call at a time with durable result handles."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

import modal

from modal_connection import fresh_client, is_connection_failure
from run_pilot import command_json, shutdown, utc
from study_budget import forecast_model, require_headroom, resource_estimate


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def make_forecast(config, models, prior):
    rates = json.loads(Path("results/metadata/modal-rates-20261028.json").read_text())["rates"]
    hourly = (
        float(rates["gpu_hour_cost_a10g"])
        + 4 * float(rates["cpu_hour_cost"])
        + 16 * float(rates["mem_gib_hour_cost"])
    )
    pilot = json.loads(
        Path("results/pilot-20261028T050156Z/Qwen2.5-1.5B-Instruct.json").read_text()
    )
    entries = []
    for model in models:
        factor = config["runtime_factors"][model["id"]]
        f = forecast_model(pilot, factor, repetitions=config["timing_repetitions"])
        f.update(
            model=model["id"],
            extrapolation_factor=factor,
            forecast_usd=resource_estimate(f["forecast_seconds"], hourly),
            reservation_usd=resource_estimate(f["execution_limit_seconds"] + 120, hourly, 0.03),
        )
        entries.append(f)
    return {
        "created_at": utc(),
        "gpu": "NVIDIA A10",
        "resource_ceiling_hourly_usd": hourly,
        "prior_project_estimate_usd": prior,
        "non_gpu_and_egress_allowance_usd": config["non_gpu_allowance_usd"],
        "models": entries,
        "forecast_study_usd": sum(e["forecast_usd"] for e in entries)
        + config["non_gpu_allowance_usd"],
        "conservative_study_usd": sum(e["reservation_usd"] for e in entries)
        + config["non_gpu_allowance_usd"],
        "basis": "Qwen1.5B A10 pilot decode times scaled by workload and explicit model factors; forecasts are not measured costs",
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--execute", action="store_true")
    args = p.parse_args()
    config_path = Path("experiments/full-study.json")
    config = json.loads(config_path.read_text())
    models = json.loads(Path("experiments/full-models.json").read_text())
    ledger_path = Path("results/budget-ledger.json")
    ledger = json.loads(ledger_path.read_text())
    prior = sum(e.get("estimated_spend_usd", 0) + e["reserved_usd"] for e in ledger["entries"])
    forecast = make_forecast(config, models, prior)
    save(Path("experiments/full-forecast.json"), forecast)
    print(json.dumps(forecast, indent=2), flush=True)
    if not args.execute:
        return
    if config["launch_status"] != "authorized_after_checks":
        raise RuntimeError("full study already submitted or lacks authorization")
    if len(models) != 6 or config["gpu"] != "A10":
        raise RuntimeError("the approved study requires six models and A10 only")
    deadline = datetime.fromisoformat(config["finish_before_utc"])
    if (deadline - datetime.now(timezone.utc)).total_seconds() < sum(
        x["execution_limit_seconds"] + config["queue_limit_seconds"] for x in forecast["models"]
    ) + 900:
        raise RuntimeError("not enough time to finish before the deadline")
    if prior + forecast["conservative_study_usd"] > 12:
        raise RuntimeError("conservative full-study forecast crosses $12; do not launch")
    for row in forecast["models"]:
        require_headroom(prior, row["reservation_usd"])
    manifest = json.loads(Path("experiments/subset.json").read_text())
    item_path = Path("experiments/bfcl-items.jsonl")
    if hashlib.sha256(item_path.read_bytes()).hexdigest() != manifest["file_sha256"]:
        raise RuntimeError("frozen benchmark changed")
    indices = {item: i for i, item in enumerate(manifest["full_ids"])}
    items = [
        {
            "item_id": r["item_id"],
            "messages": r["messages"],
            "messages_sha256": r["messages_sha256"],
            "seed_index": indices[r["item_id"]],
        }
        for r in map(json.loads, item_path.read_text().splitlines())
        if r["item_id"] in indices
    ]
    if len(items) != 500:
        raise RuntimeError("expected 500 frozen benchmark items")
    from dotenv import load_dotenv
    import os

    load_dotenv(".env")
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if not token:
        token_path = Path(
            os.environ.get(
                "HF_TOKEN_PATH",
                str(
                    Path(os.environ.get("HF_HOME", str(Path.home() / ".cache/huggingface")))
                    / "token"
                ),
            )
        )
        token = token_path.read_text().strip() if token_path.exists() else None
    if not token:
        raise RuntimeError("existing HF credential required for the authorized gated model")
    secret = modal.Secret.from_dict({"HF_TOKEN": token})
    del token
    session = Path("results/study-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    session.mkdir(parents=True)
    save(session / "apps-before.json", command_json("app", "list", "--json"))
    save(session / "billing-before.json", command_json("billing", "summary", "--json"))
    save(session / "config.json", config)
    save(session / "models.json", models)
    save(session / "forecast.json", forecast)
    save(session / "authorization.json", {"scope": "six models, A10 only", "at": utc()})
    entry = {
        "session": str(session),
        "started_at": utc(),
        "reserved_usd": config["non_gpu_allowance_usd"],
        "estimated_spend_usd": 0,
        "actual_invoice_usd": None,
        "status": "cpu_preflight_in_progress",
        "model_receipts": [],
    }
    ledger["entries"].append(entry)
    save(ledger_path, ledger)
    config_path.write_text(
        json.dumps(dict(config, launch_status="submitted_no_job_retries"), indent=2) + "\n"
    )
    image = (
        modal.Image.from_id(config["cached_image_id"])
        .add_local_file("scripts/gpu_worker.py", "/opt/gpu_worker.py", copy=True)
        .run_commands(
            "python /opt/compiler_smoke.py --output /opt/compiler-preflight.json",
            "pip-audit --progress-spinner off --ignore-vuln PYSEC-2026-3447 --ignore-vuln GHSA-xmj3-9gf7-h52w --format json --output /opt/full-image-audit.json",
        )
    )
    app = modal.App("evalnoise-study", tags={"project": "evalnoise", "session": session.name})

    @app.function(
        image=image,
        gpu="A10",
        cpu=(2, 4),
        memory=(8192, 16384),
        secrets=[secret],
        max_containers=1,
        retries=0,
        timeout=7200,
        startup_timeout=1800,
        scaledown_window=60,
        serialized=True,
        include_source=False,
    )
    def run_model(payload):
        import json
        from datetime import datetime, timezone
        from pathlib import Path
        import os
        import signal
        import subprocess
        import sys
        import tempfile
        import threading
        import time

        start = time.monotonic()
        result = {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "model": payload["model"]["id"],
            "status": "running",
            "arms": [],
            "host_load_average": os.getloadavg(),
            "host_cpu_count": os.cpu_count(),
        }
        watchdog = threading.Timer(payload["execution_limit_seconds"] + 5, lambda: os._exit(124))
        watchdog.daemon = True
        watchdog.start()
        try:
            import torch

            result["gpu"] = torch.cuda.get_device_name()
            if result["gpu"] not in {"NVIDIA A10", "NVIDIA A10G"}:
                raise RuntimeError("unexpected GPU; no cross-GPU fallback is authorized")
            result["gpu_uuid"] = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=uuid", "--format=csv,noheader"], text=True
            ).strip()
            if (
                payload.get("expected_gpu_uuid")
                and result["gpu_uuid"] != payload["expected_gpu_uuid"]
            ):
                raise RuntimeError("GPU UUID changed; stop rather than pool hardware")
            result["compiler_preflight"] = json.loads(
                Path("/opt/compiler-preflight.json").read_text()
            )
            result["image_audit"] = json.loads(Path("/opt/full-image-audit.json").read_text())
            with tempfile.TemporaryDirectory() as tmp:
                source, output = Path(tmp) / "input.json", Path(tmp) / "output.json"
                for repeat in range(payload["config"]["timing_repetitions"]):
                    order = (
                        ["default", "batch_invariant"]
                        if repeat % 2 == 0
                        else ["batch_invariant", "default"]
                    )
                    for arm in order:
                        worker = dict(payload)
                        worker["model_index"] = payload["model"]["seed_model_index"]
                        worker["timing_only"] = repeat > 0
                        worker["timing_repeat_index"] = repeat
                        source.write_text(json.dumps(worker))
                        remaining = payload["execution_limit_seconds"] - (time.monotonic() - start)
                        if remaining <= 5:
                            raise RuntimeError("per-model cost/time limit reached")
                        print(
                            f"EVALNOISE_STUDY {payload['model']['id']} repeat={repeat} arm={arm}",
                            flush=True,
                        )
                        process = subprocess.Popen(
                            [
                                sys.executable,
                                "/opt/gpu_worker.py",
                                str(source),
                                str(output),
                                "--arm",
                                arm,
                            ],
                            start_new_session=True,
                        )
                        try:
                            code = process.wait(timeout=remaining)
                            if code:
                                raise RuntimeError(f"model worker exited {code}")
                        except BaseException:
                            if process.poll() is None:
                                os.killpg(process.pid, signal.SIGKILL)
                                process.wait()
                            raise
                        value = json.loads(output.read_text())
                        if value["metadata"]["gpu"] != result["gpu"]:
                            raise RuntimeError("worker GPU mismatch")
                        for row in value["rows"]:
                            row["gpu"] = result["gpu"]
                        result["arms"].append(value)
            result["status"] = "complete"
        except Exception as exc:
            result.update(status="failed", error_type=type(exc).__name__, error=str(exc))
        finally:
            watchdog.cancel()
        result["remote_seconds"] = time.monotonic() - start
        result["ended_at"] = datetime.now(timezone.utc).isoformat()
        return result

    first_remote_start = None
    expected_gpu_uuid = None
    try:
        with fresh_client() as client:
            with app.run(client=client, detach=True):
                entry.update(app_id=app.app_id, function_id=run_model.object_id)
                save(ledger_path, ledger)
                for index, (model, f) in enumerate(zip(models, forecast["models"], strict=True)):
                    if first_remote_start:
                        current_seconds = (
                            datetime.now(timezone.utc) - first_remote_start
                        ).total_seconds() + 120
                        estimate = resource_estimate(
                            current_seconds,
                            forecast["resource_ceiling_hourly_usd"],
                            config["non_gpu_allowance_usd"],
                        )
                    else:
                        estimate = config["non_gpu_allowance_usd"]
                    require_headroom(prior + estimate, f["reservation_usd"])
                    entry.update(
                        estimated_spend_usd=estimate,
                        reserved_usd=f["reservation_usd"],
                        status="model_in_progress",
                    )
                    save(ledger_path, ledger)
                    print(
                        f"BUDGET_GATE model={index + 1}/6 estimate_total=${prior + estimate:.4f} next_reservation=${f['reservation_usd']:.4f}",
                        flush=True,
                    )
                    payload = {
                        "model": model,
                        "items": items,
                        "timing_item_ids": manifest["pilot_ids"],
                        "config": config,
                        "execution_limit_seconds": f["execution_limit_seconds"],
                        "expected_gpu_uuid": expected_gpu_uuid,
                    }
                    handle_path = session / f"model-{index}-handle.json"
                    # One submission per model. An uncertain acknowledgement is never resubmitted.
                    call = run_model.spawn(payload)
                    save(
                        handle_path,
                        {
                            "app_id": app.app_id,
                            "function_id": run_model.object_id,
                            "call_id": call.object_id,
                            "model": model["id"],
                            "submitted_at": utc(),
                        },
                    )
                    submitted = time.monotonic()
                    started = False
                    reconnects = 0
                    while True:
                        try:
                            result = call.get(timeout=30)
                            break
                        except TimeoutError:
                            stats = run_model.get_current_stats()
                            started = started or stats.num_running_inputs > 0
                            waited = time.monotonic() - submitted
                            print(
                                f"STUDY_HEARTBEAT model={index + 1} elapsed={waited:.0f}s running={stats.num_running_inputs} backlog={stats.backlog}",
                                flush=True,
                            )
                            if not started and waited >= config["queue_limit_seconds"]:
                                raise RuntimeError("no A10 available within 30 minutes; stopping")
                            if (
                                waited
                                > f["execution_limit_seconds"] + config["queue_limit_seconds"] + 60
                            ):
                                raise RuntimeError("bounded model wait expired")
                        except Exception as exc:
                            if reconnects or not is_connection_failure(exc):
                                raise
                            reconnects += 1
                            save(
                                session / f"model-{index}-connection-recovery.json",
                                {
                                    "call_id": call.object_id,
                                    "at": utc(),
                                    "error_type": type(exc).__name__,
                                },
                            )
                            with fresh_client() as recovered:
                                result = modal.FunctionCall.from_id(
                                    call.object_id, client=recovered
                                ).get(
                                    timeout=f["execution_limit_seconds"]
                                    + config["queue_limit_seconds"]
                                )
                            break
                    save(session / (model["id"].rsplit("/", 1)[-1] + ".json"), result)
                    if first_remote_start is None:
                        first_remote_start = datetime.fromisoformat(result["started_at"])
                        expected_gpu_uuid = result.get("gpu_uuid")
                    current_seconds = (
                        datetime.now(timezone.utc) - first_remote_start
                    ).total_seconds() + 120
                    estimate = resource_estimate(
                        current_seconds,
                        forecast["resource_ceiling_hourly_usd"],
                        config["non_gpu_allowance_usd"],
                    )
                    entry["model_receipts"].append(
                        {
                            "model": model["id"],
                            "remote_seconds": result["remote_seconds"],
                            "forecast_seconds": f["forecast_seconds"],
                            "execution_limit_seconds": f["execution_limit_seconds"],
                            "estimated_project_total_after_model_usd": prior + estimate,
                            "call_id": call.object_id,
                            "status": result["status"],
                        }
                    )
                    entry.update(estimated_spend_usd=estimate, reserved_usd=0)
                    save(ledger_path, ledger)
                    save(session / "budget-checks.json", entry["model_receipts"])
                    print(
                        f"MODEL_COMPLETE {model['id']} status={result['status']} total_estimate=${prior + estimate:.4f}",
                        flush=True,
                    )
                    if result["status"] != "complete":
                        raise RuntimeError(
                            "model worker failed; no job retry: " + result.get("error", "unknown")
                        )
                    save(
                        session / "calls-latest.json",
                        command_json("function", "calls", run_model.object_id, "--json"),
                    )
                entry["status"] = "inference_complete_needs_scoring"
    except BaseException as exc:
        entry.update(
            status="stopped_incomplete_no_job_retry", error_type=type(exc).__name__, error=str(exc)
        )
        raise
    finally:
        entry["ended_at"] = utc()
        try:
            shutdown(
                session / "shutdown.json",
                own_app_id=entry.get("app_id") or app.app_id,
                stop_all=False,
            )
        finally:
            save(session / "billing-after.json", command_json("billing", "summary", "--json"))
            save(session / "apps-final.json", command_json("app", "list", "--json"))
            save(session / "containers-final.json", command_json("container", "list", "--json"))
            if entry.get("function_id"):
                calls = command_json("function", "calls", entry["function_id"], "--json")
                stats = command_json("function", "stats", entry["function_id"], "--json")
                save(session / "final-calls.json", calls)
                save(session / "final-stats.json", stats)
                startup = (
                    stats.get("container_percentile_stats", {})
                    .get("Startup time (s)", {})
                    .get("percentiles", {})
                    .get("p50", 0)
                )
                timed_seconds = sum(c.get("execution_time_seconds", 0) or 0 for c in calls) + (
                    startup + 60
                ) * stats.get("container_total_count", 0)
                if first_remote_start:
                    final_seconds = (
                        datetime.now(timezone.utc) - first_remote_start
                    ).total_seconds() + 120
                    timed_seconds = max(timed_seconds, final_seconds)
                entry["estimated_spend_usd"] = resource_estimate(
                    timed_seconds,
                    forecast["resource_ceiling_hourly_usd"],
                    config["non_gpu_allowance_usd"],
                )
            entry["reserved_usd"] = 0
            save(ledger_path, ledger)
            print(f"STUDY_SESSION {session} status={entry['status']}", flush=True)


if __name__ == "__main__":
    with modal.enable_output():
        main()
