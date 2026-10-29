"""Run one bounded model on an already allocated A10; no job submission code."""


def execute_model(payload):
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
        if payload.get("expected_gpu_uuid") and result["gpu_uuid"] != payload["expected_gpu_uuid"]:
            raise RuntimeError("GPU UUID changed; stop rather than pool hardware")
        result["compiler_preflight"] = json.loads(Path("/opt/compiler-preflight.json").read_text())
        result["image_audit"] = json.loads(Path("/opt/full-image-audit.json").read_text())
        with tempfile.TemporaryDirectory() as tmp:
            source, output = (Path(tmp) / "input.json", Path(tmp) / "output.json")
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
