"""Report a completed single model without implying the six-model study finished."""

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np

from evalnoise.cli import greedy
from evalnoise.data import load
from evalnoise.stats import analyze
from study_analysis import wilson


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("session", type=Path)
    args = parser.parse_args()
    session = args.session
    job = json.loads((session / "Qwen2.5-1.5B-Instruct.json").read_text())
    if job["status"] != "complete":
        raise ValueError("model incomplete")
    out = session / "partial-model1"
    out.mkdir(exist_ok=True)
    rows = [r for arm in job["arms"] for r in arm["rows"]]
    if len(rows) != 9800:
        raise ValueError("expected 9,800 saved predictions")
    raw, scored = out / "raw.jsonl", out / "scored.jsonl"
    raw.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    subprocess.run(
        [".venv-bfcl/bin/python", "scripts/score_bfcl.py", str(raw), str(scored)], check=True
    )
    rows = [json.loads(r) for r in scored.read_text().splitlines()]
    primary = [r for r in rows if r["phase"] == "evaluation"]
    models, items, data = load(scored, condition="sampling")
    result = analyze(models, items, data, ks=[1, 5, 10], seed=20261101, resamples=5000)
    result["provenance"] = {
        "input_sha256": hashlib.sha256(scored.read_bytes()).hexdigest(),
        "scope": "one completed model; no pairwise inference",
    }
    (out / "analysis-sampling.json").write_text(json.dumps(result, indent=2) + "\n")
    summaries = {}
    name = models[0]
    for arm in ("default", "batch_invariant"):
        arm_rows = [r for r in primary if r["temperature"] == 0 and r["arm"] == arm]
        g = greedy(arm_rows)["models"][name]
        if g["n_items"] != 500:
            raise ValueError("expected 500 aligned greedy items")
        g["text_change_ci95"] = wilson(g["changed_items"], 500)
        grouped = defaultdict(list)
        for r in arm_rows:
            grouped[r["item_id"]].append(r)
        g["token_changed_items"] = sum(
            len({tuple(r["token_ids"]) for r in cell}) > 1 for cell in grouped.values()
        )
        g["scores"] = {
            run: float(np.mean([r["passed"] for r in arm_rows if r["run_id"] == run]))
            for run in ("serial", "batch8", "batch32")
        }
        summaries[arm] = g
    timing = {}
    for arm in job["arms"]:
        for t in arm["metadata"]["timings"]:
            if t["phase"] == "timing":
                timing[t["arm"], t["run_id"], t["repeat_index"]] = t
    ratios = []
    for run in ("serial", "batch8", "batch32"):
        values = [
            timing["batch_invariant", run, r]["generated_tokens_per_second"]
            / timing["default", run, r]["generated_tokens_per_second"]
            for r in range(3)
        ]
        completion = [
            timing["batch_invariant", run, r]["completions_per_second"]
            / timing["default", run, r]["completions_per_second"]
            for r in range(3)
        ]
        ratios.append(
            {
                "configuration": run,
                "token_rate_ratios": values,
                "token_rate_median": float(np.median(values)),
                "token_rate_range": [min(values), max(values)],
                "completion_rate_ratios": completion,
                "completion_rate_median": float(np.median(completion)),
                "completion_rate_range": [min(completion), max(completion)],
            }
        )
    summary = {
        "model": name,
        "completed_models": 1,
        "planned_models": 6,
        "gpu": job["gpu"],
        "gpu_uuid": job["gpu_uuid"],
        "scored_predictions": len(rows),
        "primary_predictions": len(primary),
        "timing_predictions": len(rows) - len(primary),
        "truncations": sum(r["finish_reason"] == "length" for r in rows),
        "greedy": summaries,
        "throughput": ratios,
        "remote_seconds": job["remote_seconds"],
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    receipt = json.loads((session / "interruption-receipt.json").read_text())
    lines = [
        "# Partial study: one completed model",
        "",
        "**The six-model study is incomplete.** Qwen2.5-1.5B finished; the app stopped before model two was accepted. No pairwise flip rate can be estimated from this single model. Saved outputs are retained and must not be rerun.",
        "",
        "## Sampling accuracy",
        "",
        "500 frozen BFCL items, temperature .7, n=10. Official BFCL scoring; 5,000 item-bootstrap draws.",
        "",
        "| Metric | Estimate | Item-bootstrap 95% CI |",
        "|---|---:|---|",
    ]
    for metric, modes in result["metrics"].items():
        r = modes["items"]["models"][name]
        lines.append(f"| {metric} | {r['estimate']:.2%} | [{r['ci'][0]:.2%}, {r['ci'][1]:.2%}] |")
    lines += [
        "",
        "## Greedy sensitivity",
        "",
        "| Arm | Text changed / 500 | Wilson 95% interval | Token IDs changed | Correctness changed | Scores at 1 / 8 / 32 |",
        "|---|---:|---|---:|---:|---|",
    ]
    for arm, g in summaries.items():
        lo, hi = g["text_change_ci95"]
        scores = " / ".join(f"{s:.1%}" for s in g["scores"].values())
        lines.append(
            f"| {arm} | {g['changed_items']} | [{lo:.2%}, {hi:.2%}] | {g['token_changed_items']} | {g['score_changed_fraction']:.1%} | {scores} |"
        )
    lines += [
        "",
        "## Three matched throughput repetitions",
        "",
        "Ratios are invariant/default. These describe this A10 configuration, without a general production performance claim.",
        "",
        "| Batch | Token-rate median | Token-rate range | Completion-rate median | Completion-rate range |",
        "|---|---:|---|---:|---|",
    ]
    for r in ratios:
        lo, hi = r["token_rate_range"]
        clo, chi = r["completion_rate_range"]
        lines.append(
            f"| {r['configuration']} | {r['token_rate_median']:.3f} | [{lo:.3f}, {hi:.3f}] | {r['completion_rate_median']:.3f} | [{clo:.3f}, {chi:.3f}] |"
        )
    lines += [
        "",
        "## Time, cost, and limits",
        "",
        f"Execution took {job['remote_seconds']:.2f}s versus 2,072.68s forecast. Modal reports ${receipt['metered_app_usage_usd']} in app-specific gross usage. The conservative stopped-app resource estimate plus setup/egress margin is ${float(receipt['estimated_session_spend_usd']):.6f}. Settled invoice actuals are unknown. Post-stop client waiting is excluded from compute cost.",
        "",
        f"All {len(rows):,} saved predictions were scored, including {len(rows) - len(primary):,} separate timing predictions. Truncations: {summary['truncations']}. Timing rows never inflate primary accuracy samples. Text-change intervals assume independent items. These observations concern {job['gpu']} and the pinned setup. They cannot establish six-model rankings or close-pair flip rates.",
        "",
        "All evalnoise apps are stopped and holds released. qunti-check was not modified. The prepared remaining-five job requires approval because its forecast exceeds $5.",
    ]
    (out / "REPORT.md").write_text("\n".join(lines) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
