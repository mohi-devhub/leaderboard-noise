"""One durable pilot call, with ordered GPU fallback and connection-only recovery."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import modal


def utc():
    return datetime.now(timezone.utc).isoformat()


def command_json(*args):
    return json.loads(subprocess.check_output([sys.executable, "-m", "modal", *args], text=True))


def shutdown(out, *, own_app_id=None, stop_all=False):
    import time

    def in_scope(app):
        return stop_all or app.get("app_id", app.get("App ID", app.get("id"))) == own_app_id

    apps = command_json("app", "list", "--json")
    for app in apps:
        if not in_scope(app):
            continue
        state = str(app.get("State", app.get("state", ""))).lower()
        if state in {"stopped", "disabled", "stopping"}:
            continue
        app_id = app.get("App ID", app.get("app_id", app.get("id")))
        if not app_id:
            raise RuntimeError("cannot identify active Modal app for shutdown")
        stopped = subprocess.run(
            [sys.executable, "-m", "modal", "app", "stop", app_id, "--yes"],
            text=True,
            capture_output=True,
        )
        if (
            stopped.returncode
            and "already stopped" not in (stopped.stdout + stopped.stderr).lower()
        ):
            raise RuntimeError(f"failed to stop Modal app {app_id}")
    for _ in range(15):
        final = command_json("app", "list", "--json")
        if all(
            str(a.get("State", a.get("state", ""))).lower() in {"stopped", "disabled"}
            for a in final
            if in_scope(a)
        ):
            break
        time.sleep(2)
    out.write_text(
        json.dumps(
            {
                "checked_at": utc(),
                "scope": "all apps" if stop_all else "this app only",
                "apps": final,
            },
            indent=2,
        )
        + "\n"
    )
    active = [
        a
        for a in final
        if in_scope(a)
        and str(a.get("State", a.get("state", ""))).lower() not in {"stopped", "disabled"}
    ]
    if active:
        raise RuntimeError("Modal still reports active apps; inspect shutdown evidence")


def pilot_items(item_path, manifest):
    """Retain fixed seed indices while excluding scorer answers from GPU payloads."""
    indices = {item_id: i for i, item_id in enumerate(manifest["full_ids"])}
    selected = set(manifest["pilot_ids"])
    return [
        {
            "item_id": r["item_id"],
            "messages": r["messages"],
            "messages_sha256": r["messages_sha256"],
            "seed_index": indices[r["item_id"]],
        }
        for r in map(json.loads, item_path.read_text().splitlines())
        if r["item_id"] in selected
    ]


def main():
    from modal_connection import fresh_client, wait_existing_call

    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true", help="launch the authorized pilot")
    parser.add_argument(
        "--preserve-other-apps",
        action="store_true",
        help="stop only this pilot app if the user asks to preserve concurrent work",
    )
    args = parser.parse_args()
    config = json.loads(Path("experiments/pilot.json").read_text())
    deadline = datetime.fromisoformat(config["finish_before_utc"])
    if (deadline - datetime.now(timezone.utc)).total_seconds() < config[
        "job_timeout_seconds"
    ] + 900:
        raise RuntimeError("insufficient time to finish before the October 31 deadline")
    if args.execute and config["launch_status"] != "authorized_after_security_checks":
        raise RuntimeError(
            "pilot retry requires the user's decision; record it before changing launch_status"
        )
    models = {m["id"]: m for m in json.loads(Path("experiments/models.json").read_text())}
    manifest = json.loads(Path("experiments/subset.json").read_text())
    item_path = Path("experiments/bfcl-items.jsonl")
    if hashlib.sha256(item_path.read_bytes()).hexdigest() != manifest["file_sha256"]:
        raise RuntimeError("frozen benchmark bytes changed")
    items = pilot_items(item_path, manifest)
    if len(items) != 100 or len(config["models"]) != 2:
        raise RuntimeError("this entry point only authorizes the 2x100 pilot")
    reserve = len(config["models"]) * config["max_reserved_usd_per_model"]
    ledger_path = Path("results/budget-ledger.json")
    ledger = json.loads(ledger_path.read_text())
    previous = sum(e["reserved_usd"] + e.get("estimated_spend_usd", 0) for e in ledger["entries"])
    if reserve > ledger["batch_approval_threshold_usd"] or previous + reserve > ledger["cap_usd"]:
        raise RuntimeError("budget gate: ask the user before this batch")
    print(f"Pilot reservation ${reserve:.2f}; cumulative reservation ${previous + reserve:.2f}/$12")
    if not args.execute:
        return
    if ledger.get("retry_authorization", {}).get("remaining_retry_count") != 1:
        raise RuntimeError("no unused authorized pilot retry remains")
    for filename in ("audit-local.json", "audit-bfcl.json", "audit-gpu.json"):
        audit = json.loads((Path("results") / filename).read_text())
        accepted = (
            {"PYSEC-2026-3447", "GHSA-xmj3-9gf7-h52w"} if filename == "audit-gpu.json" else set()
        )
        findings = [v for d in audit["dependencies"] for v in d.get("vulns", [])]
        if any(v["id"] not in accepted for v in findings):
            raise RuntimeError(f"unaccepted vulnerability in {filename}")
    session = Path("results/pilot-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    session.mkdir(parents=True)
    (session / "billing-before.json").write_text(
        json.dumps(command_json("billing", "summary", "--json"), indent=2)
    )
    entry = {
        "session": str(session),
        "started_at": utc(),
        "reserved_usd": reserve,
        "status": "reserved_before_launch",
        "actual_invoice_usd": None,
        "estimated_spend_usd": 0,
    }
    ledger["entries"].append(entry)
    ledger["retry_authorization"]["remaining_retry_count"] = 0
    ledger_path.write_text(json.dumps(ledger, indent=2) + "\n")
    (session / "config.json").write_text(json.dumps(config, indent=2) + "\n")
    config_path = Path("experiments/pilot.json")
    updated_config = dict(config, launch_status="authorized_retry_in_progress_no_further_retry")
    config_path.write_text(json.dumps(updated_config, indent=2) + "\n")
    # Reuse the immutable compiler-equipped image built in the approved prior attempt.
    audit_file = "/opt/image-audit-" + datetime.now(timezone.utc).strftime("%Y%m%d") + ".json"
    image = modal.Image.from_id(config["cached_image_id"]).run_commands(
        "python /opt/compiler_smoke.py --output /opt/compiler-preflight.json",
        "pip-audit --progress-spinner off --ignore-vuln PYSEC-2026-3447 --ignore-vuln GHSA-xmj3-9gf7-h52w --format json --output "
        + audit_file,
    )
    app = modal.App("evalnoise-pilot", tags={"project": "evalnoise", "session": session.name})

    @app.function(
        image=image,
        gpu=config["gpu_priority"],
        cpu=(2, 4),
        memory=(8192, 16384),
        max_containers=1,
        retries=0,
        timeout=config["job_timeout_seconds"],
        startup_timeout=900,
        scaledown_window=2,
        serialized=True,
        include_source=False,
    )
    def run_pilot_job(payload):
        import json
        from pathlib import Path
        import subprocess
        import sys
        import tempfile
        import time

        started = time.perf_counter()
        result = {"status": "running", "arms": [], "smoke": None}
        try:
            import os
            import torch

            actual_gpu = torch.cuda.get_device_name()
            result["gpu"] = actual_gpu
            result["cuda"] = torch.version.cuda
            result["host_load_average"] = os.getloadavg()
            result["host_cpu_count"] = os.cpu_count()
            result["compiler_preflight"] = json.loads(
                Path("/opt/compiler-preflight.json").read_text()
            )
            result["image_audit"] = json.loads(Path(payload["audit_file"]).read_text())
            print("EVALNOISE_GPU " + actual_gpu, flush=True)
            with tempfile.TemporaryDirectory() as directory:

                def worker(model_index, arm, smoke_only=False):
                    model = payload["models"][model_index]
                    source = Path(directory) / "payload.json"
                    source.write_text(
                        json.dumps(
                            {
                                "config": payload["config"],
                                "model": model,
                                "items": payload["items"],
                                "model_index": model_index,
                            }
                        )
                    )
                    output = Path(directory) / "output.json"
                    command = [
                        sys.executable,
                        "/opt/gpu_worker.py",
                        str(source),
                        str(output),
                        "--arm",
                        arm,
                    ]
                    if smoke_only:
                        command.append("--smoke-only")
                    subprocess.run(command, check=True, timeout=600 if smoke_only else 1740)
                    value = json.loads(output.read_text())
                    worker_gpu = value["gpu"] if smoke_only else value["metadata"]["gpu"]
                    if worker_gpu != actual_gpu:
                        raise RuntimeError("GPU changed within the pilot")
                    return value

                print("EVALNOISE_STAGE five_request_smoke", flush=True)
                result["smoke"] = worker(0, "default", True)
                if not result["smoke"]["passed"] or result["smoke"]["requests"] != 5:
                    raise RuntimeError("five-request smoke gate failed")
                print("EVALNOISE_STAGE smoke_passed", flush=True)
                for index in range(len(payload["models"])):
                    for arm in payload["config"]["arms"]:
                        result["stage"] = {"model": payload["models"][index]["id"], "arm": arm}
                        print("EVALNOISE_STAGE " + json.dumps(result["stage"]), flush=True)
                        arm_result = worker(index, arm)
                        for row in arm_result["rows"]:
                            row["gpu"] = actual_gpu
                        result["arms"].append(arm_result)
                        print("EVALNOISE_ARM_COMPLETE " + json.dumps(result["stage"]), flush=True)
            result["status"] = "complete"
        except Exception as exc:
            result["status"] = "failed"
            result["error_type"] = type(exc).__name__
            result["error"] = str(exc)
            print("EVALNOISE_INFRA_FAILURE " + type(exc).__name__, flush=True)
        result["remote_seconds"] = time.perf_counter() - started
        return result

    def record_reconnect(call_id, error_type):
        if ledger["retry_authorization"]["remaining_connection_retry_count"] != 1:
            raise RuntimeError("the single connection reconnection is exhausted")
        ledger["retry_authorization"]["remaining_connection_retry_count"] = 0
        entry["connection_recovery"] = {"call_id": call_id, "error_type": error_type, "at": utc()}
        ledger_path.write_text(json.dumps(ledger, indent=2) + "\n")
        print("Reconnecting once to existing call " + call_id, flush=True)

    try:
        entry["status"] = "cpu_image_preflight_in_progress"
        ledger_path.write_text(json.dumps(ledger, indent=2) + "\n")
        with fresh_client() as client:
            with app.run(client=client, detach=True):
                entry["app_id"] = app.app_id
                entry["function_id"] = run_pilot_job.object_id
                entry["cpu_image_preflight_passed_at"] = utc()
                ledger_path.write_text(json.dumps(ledger, indent=2) + "\n")
                payload = {
                    "config": config,
                    "items": items,
                    "audit_file": audit_file,
                    "models": [models[name] for name in config["models"]],
                }
                # Submit once. A lost acknowledgement is reconciled by listing calls, never respawning.
                try:
                    call = run_pilot_job.spawn(payload)
                except Exception as exc:
                    from modal_connection import is_connection_failure

                    if not is_connection_failure(exc):
                        raise
                    record_reconnect("submission_acknowledgement_unknown", type(exc).__name__)
                    candidates = command_json(
                        "function", "calls", run_pilot_job.object_id, "--json"
                    )
                    if len(candidates) != 1:
                        raise RuntimeError(
                            "cannot safely identify the submitted job; refusing resubmission"
                        ) from exc
                    call = modal.FunctionCall.from_id(candidates[0]["function_call_id"])
                entry["call_id"] = call.object_id
                entry["status"] = "durable_pilot_running"
                ledger_path.write_text(json.dumps(ledger, indent=2) + "\n")
                (session / "job-handle.json").write_text(
                    json.dumps(
                        {
                            "app_id": app.app_id,
                            "call_id": call.object_id,
                            "function_id": run_pilot_job.object_id,
                        },
                        indent=2,
                    )
                    + "\n"
                )
                result = wait_existing_call(
                    call, config["job_timeout_seconds"] + 900, record_reconnect
                )
                (session / "job-result.json").write_text(json.dumps(result, indent=2) + "\n")
                entry["selected_gpu"] = result.get("gpu")
                if result.get("smoke"):
                    (session / "gpu-smoke.json").write_text(
                        json.dumps(result["smoke"], indent=2) + "\n"
                    )
                for name in config["models"]:
                    arms = [r for r in result["arms"] if r["metadata"]["model"]["id"] == name]
                    if arms:
                        (session / (name.rsplit("/", 1)[-1] + ".json")).write_text(
                            json.dumps({"arms": arms}, indent=2) + "\n"
                        )
                if result["status"] != "complete":
                    raise RuntimeError(
                        "pilot worker failed: "
                        + result.get("error", "unknown infrastructure error")
                    )
                entry["status"] = "inference_complete_needs_scoring"
                updated_config["launch_status"] = "pilot_complete_waiting_for_full_run_approval"
    except BaseException as exc:
        entry["status"] = "failed_no_job_retry"
        entry["error_type"] = type(exc).__name__
        updated_config["launch_status"] = "retry_failed_no_additional_retry_authorized"
        raise
    finally:
        entry["ended_at"] = utc()
        ledger_path.write_text(json.dumps(ledger, indent=2) + "\n")
        config_path.write_text(json.dumps(updated_config, indent=2) + "\n")
        try:
            shutdown(
                session / "shutdown.json",
                own_app_id=entry.get("app_id") or app.app_id,
                stop_all=False,
            )
        finally:
            (session / "billing-after.json").write_text(
                json.dumps(command_json("billing", "summary", "--json"), indent=2)
            )
    print(f"Inference artifacts: {session}. Stop here for pilot analysis and user review.")


if __name__ == "__main__":
    with modal.enable_output():
        main()
