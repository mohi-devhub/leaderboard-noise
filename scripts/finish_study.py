"""Finish one existing study's CPU analysis after its controller has stopped the app."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("session", type=Path)
    parser.add_argument("--wait", action="store_true")
    args = parser.parse_args()
    session = args.session
    deadline = datetime.fromisoformat(
        json.loads((session / "config.json").read_text())["finish_before_utc"]
    )
    while True:
        ledger = json.loads(Path("results/budget-ledger.json").read_text())
        entry = next(e for e in ledger["entries"] if e["session"] == str(session))
        if entry["status"] == "stopped_incomplete_no_job_retry":
            raise RuntimeError(
                "controller stopped incomplete; do not manufacture a completed report"
            )
        if (
            entry["status"] == "inference_complete_needs_scoring"
            and (session / "final-stats.json").exists()
            and entry["reserved_usd"] == 0
        ):
            break
        if entry["status"] == "full_study_scored_apps_stopped":
            print("Study already analyzed; refusing to repeat work without an explicit command.")
            return
        if not args.wait:
            raise RuntimeError("inference/cleanup is not complete")
        if datetime.now(timezone.utc) >= deadline:
            raise RuntimeError("analysis wait reached the study deadline")
        print(
            f"WAIT_EXISTING_STUDY status={entry['status']} completed_models={len(entry['model_receipts'])}/6",
            flush=True,
        )
        time.sleep(30)
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
        print("CPU_ANALYSIS " + " ".join(command), flush=True)
        subprocess.run(command, env=env, check=True)
    cli = json.loads((session / "cli-analysis.json").read_text())
    analysis = json.loads((session / "analysis-sampling.json").read_text())
    if cli["metrics"] != analysis["metrics"]:
        raise RuntimeError("installed CLI does not match the report")
    source_paths = [
        *Path("scripts").glob("*.py"),
        *Path("src/evalnoise").glob("*.py"),
        session / "REPORT.md",
        session / "scored.jsonl",
        session / "receipt.json",
    ]
    verification = {
        "at": datetime.now(timezone.utc).isoformat(),
        "official_scoring_and_coverage": "passed",
        "installed_cli_metrics_exact_match": True,
        "figures_generated": True,
        "sha256": {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths},
    }
    (session / "verification.json").write_text(json.dumps(verification, indent=2) + "\n")
    print("STUDY_CPU_ANALYSIS_COMPLETE " + str(session), flush=True)


if __name__ == "__main__":
    main()
