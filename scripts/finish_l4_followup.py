"""Wait for the existing observer's receipt, then run CPU analysis; never submit a job."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from run_pilot import utc


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("session", type=Path)
    args = parser.parse_args()
    session = args.session
    while not (session / "receipt.json").exists():
        log = (session / "observer.log").read_text()
        if "Traceback" in log:
            raise RuntimeError(
                "observer needs recovery of existing handles; never resubmit GPU work"
            )
        time.sleep(30)
    receipt = json.loads((session / "receipt.json").read_text())
    if (
        receipt["estimated_spend_usd"] > 5
        or receipt["project_estimate_usd"] > 12
        or not receipt["own_apps_stopped"]
        or receipt["own_running_containers"]
        or receipt["active_reservations_usd"]
    ):
        raise RuntimeError("cost or cleanup receipt needs reconciliation")
    env = dict(os.environ, MPLCONFIGDIR=".uv-cache/matplotlib")
    subprocess.run(
        [sys.executable, "scripts/report_l4_followup.py", str(session)], check=True, env=env
    )
    if not (session / "summary.json").exists():
        print("L4_ANALYSIS_INCOMPLETE_NO_COMPLETE_MODEL", flush=True)
        return
    subprocess.run(
        [
            sys.executable,
            "scripts/l4_figures.py",
            str(session),
            "--out",
            "figures/" + session.name,
        ],
        check=True,
        env=env,
    )
    cli = subprocess.run(
        [
            ".venv/bin/evalnoise",
            "analyze",
            str(session / "scored.jsonl"),
            "--condition",
            "default:serial",
            "--output",
            str(session / "cli-analysis.json"),
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    (session / "cli-output.txt").write_text(cli.stdout)
    actual = json.loads((session / "cli-analysis.json").read_text())
    expected = json.loads((session / "analysis-default-serial.json").read_text())
    if actual["metrics"] != expected["metrics"]:
        raise RuntimeError("installed CLI metrics differ from the report")
    summary = json.loads((session / "summary.json").read_text())
    (session / "analysis-verification.json").write_text(
        json.dumps(
            {
                "at": utc(),
                "status": summary["status"],
                "scored_predictions": summary["predictions"],
                "installed_cli_exact_metric_match": True,
                "own_apps_stopped": True,
                "cost_caps_verified": True,
            },
            indent=2,
        )
        + "\n"
    )
    print("L4_ANALYSIS_" + summary["status"].upper(), flush=True)


if __name__ == "__main__":
    main()
