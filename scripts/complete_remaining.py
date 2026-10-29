"""Observe saved calls/checkpoints and finalize; this command cannot submit GPU jobs."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import modal

from modal_connection import fresh_client
from run_remaining import download_results, reconcile_stopped, save


def main():
    p = argparse.ArgumentParser()
    p.add_argument("session", type=Path)
    p.add_argument("--wait", action="store_true")
    args = p.parse_args()
    session = args.session
    resources = json.loads((session / "remaining-resources.json").read_text())
    handles = json.loads((session / "remaining-controller-handle.json").read_text())
    config = json.loads((session / "config.json").read_text())
    deadline = datetime.fromisoformat(config["finish_before_utc"])
    last = None
    result = None
    while not (session / "remaining-volume-deleted.json").exists():
        progress = None
        result = None
        with fresh_client() as client:
            volume = modal.Volume.from_name(resources["volume_name"], client=client)
            try:
                result = json.loads(b"".join(volume.read_file("manifest.json")))
            except (FileNotFoundError, modal.exception.NotFoundError):
                try:
                    progress = json.loads(b"".join(volume.read_file("progress.json")))
                except (FileNotFoundError, modal.exception.NotFoundError):
                    pass
            try:
                gpu_handle = json.loads(b"".join(volume.read_file("gpu-call.json")))
                save(session / "remaining-gpu-call.json", gpu_handle)
                if result is not None:
                    rpc_result = modal.FunctionCall.from_id(
                        gpu_handle["call_id"], client=client
                    ).get(timeout=30)
                    result = rpc_result
            except (FileNotFoundError, modal.exception.NotFoundError):
                pass
            if result is None:
                try:
                    controller = modal.FunctionCall.from_id(handles["call_id"], client=client).get(
                        timeout=0
                    )
                    result = controller
                except (modal.exception.FunctionTimeoutError, modal.exception.RemoteError) as exc:
                    result = dict(
                        progress or {},
                        status="failed",
                        error_type=type(exc).__name__,
                        error=str(exc),
                    )
                except TimeoutError:
                    pass
        if progress is not None:
            save(session / "remaining-progress.json", progress)
            current = [r["model"] for r in progress.get("models", [])]
            if current != last:
                print("CHECKPOINTS_VERIFIED " + json.dumps(current), flush=True)
                last = current
        if result is not None:
            save(session / "remaining-job-result.json", result)
            break
        if not args.wait:
            print("Existing detached job is still running; no submission performed.")
            return
        if datetime.now(timezone.utc) >= deadline:
            raise RuntimeError("deadline reached; inspect bounded remote watchdog and stop own app")
        time.sleep(30)
    if result is None:
        result = json.loads((session / "remaining-job-result.json").read_text())
    ledger_path = Path("results/budget-ledger.json")
    ledger = json.loads(ledger_path.read_text())
    entry = next(e for e in reversed(ledger["entries"]) if e.get("app_id") == handles["app_id"])
    original = json.loads((session / "forecast.json").read_text())
    reconcile_stopped(session, entry, ledger, ledger_path, original, result)
    result = download_results(session)
    if result["status"] != "complete":
        raise RuntimeError(
            "remaining job stopped incomplete; checkpoints preserved; never resubmit"
        )
    entry["status"] = "remaining_complete_ready_for_scoring"
    save(ledger_path, ledger)
    env = dict(os.environ, MPLCONFIGDIR=".uv-cache/matplotlib")
    commands = [
        [sys.executable, "scripts/report_study.py", str(session)],
        [sys.executable, "scripts/study_receipt.py", str(session)],
        [
            sys.executable,
            "scripts/figures.py",
            str(session / "analysis-sampling.json"),
            "--out",
            "figures/" + session.name,
        ],
        [
            sys.executable,
            "scripts/study_figures.py",
            str(session),
            "--out",
            "figures/" + session.name,
        ],
        [
            ".venv/bin/evalnoise",
            "analyze",
            str(session / "evaluation.jsonl"),
            "--condition",
            "sampling",
            "--k",
            "1",
            "5",
            "10",
            "--output",
            str(session / "cli-analysis.json"),
        ],
    ]
    for command in commands:
        print("ANALYSIS " + " ".join(command), flush=True)
        subprocess.run(command, check=True, env=env)
    cli = json.loads((session / "cli-analysis.json").read_text())
    report = json.loads((session / "analysis-sampling.json").read_text())
    if cli["metrics"] != report["metrics"]:
        raise RuntimeError("installed CLI differs from report")
    print("FULL_STUDY_ANALYZED " + str(session), flush=True)


if __name__ == "__main__":
    main()
