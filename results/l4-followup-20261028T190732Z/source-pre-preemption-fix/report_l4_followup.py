"""Score saved L4 greedy outputs and compare the preselected pairs with A10."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np

from evalnoise.data import load
from evalnoise.stats import analyze
from l4_receipt import refresh_receipt
from study_analysis import flip_summary, wilson


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def short(name):
    return name.rsplit("/", 1)[-1]


def pct(value):
    return f"{value:.2%}"


def interval(values):
    return f"[{pct(values[0])}, {pct(values[1])}]"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("session", type=Path)
    args = parser.parse_args()
    session = args.session
    approval = json.loads((session / "approval.json").read_text())
    source = Path(approval["a10_session"])
    config = json.loads((session / "config.json").read_text())
    manifest = json.loads((session / "job-result.json").read_text())
    receipt = refresh_receipt(session)
    roster = json.loads((session / "models.json").read_text())
    frozen = json.loads(Path("experiments/subset.json").read_text())
    if (
        hashlib.sha256(Path("experiments/bfcl-items.jsonl").read_bytes()).hexdigest()
        != frozen["file_sha256"]
    ):
        raise RuntimeError("frozen benchmark questions or answers changed before scoring")
    ids = frozen["full_ids"]
    names = [r["model"] for r in manifest["models"] if r["status"] == "complete"]
    missing = [m["id"] for m in roster if m["id"] not in names]
    conditions = [
        f"{arm}:{run['run_id']}" for arm in config["arms"] for run in config["greedy_repeats"]
    ]
    original = {}
    rows = []
    jobs = []
    for name in names:
        job = json.loads((session / (short(name) + ".json")).read_text())
        old = json.loads((source / (short(name) + ".json")).read_text())
        jobs.append(job)
        if job["gpu"] != "NVIDIA L4" or len(job["arms"]) != 2:
            raise RuntimeError("unexpected GPU or process count")
        for process in old["arms"]:
            for row in process["rows"]:
                if row["phase"] == "evaluation" and row["temperature"] == 0:
                    original[name, row["condition"], row["item_id"]] = row
        for process in job["arms"]:
            meta = process["metadata"]
            if meta["engine"] != old["arms"][0]["metadata"]["engine"]:
                raise RuntimeError("engine configuration changed from A10")
            for package in ("vllm", "torch", "transformers", "tokenizers"):
                if meta["packages"][package] != old["arms"][0]["metadata"]["packages"][package]:
                    raise RuntimeError("inference package version changed")
            if meta["smoke_requests"] != 5:
                raise RuntimeError("five-request smoke gate missing")
            if name.startswith("meta-llama/") and meta["tokenization_kwargs"] != {
                "add_special_tokens": False
            }:
                raise RuntimeError("Llama tokenization correction is required")
            rows.extend(process["rows"])
    if len({job["gpu_uuid"] for job in jobs}) > 1:
        raise RuntimeError("the L4 models did not share a physical device")
    expected = {
        (name, condition, item) for name in names for condition in conditions for item in ids
    }
    seen = set()
    for row in rows:
        key = row["model"], row["condition"], row["item_id"]
        if key in seen or row["phase"] != "evaluation" or row["sample_id"] != 0:
            raise RuntimeError("duplicated or non-primary prediction")
        seen.add(key)
        old = original[key]
        for field in ("revision", "messages_sha256", "rendered_prompt_sha256", "sampling_seed"):
            if row[field] != old[field]:
                raise RuntimeError("frozen checkpoint, prompt, or seed changed from A10")
        if row["temperature"] != 0 or row["gpu"] != "NVIDIA L4":
            raise RuntimeError("unexpected decoding configuration")
    if seen != expected:
        raise RuntimeError("incomplete or unexpected item coverage")
    if not names:
        (session / "REPORT.md").write_text(
            "# L4 follow-up incomplete\n\nNo complete model was collected. This is an infrastructure/budget outcome, not a scientific null result. See job-result.json and receipt.json. No GPU job retry was submitted.\n"
        )
        return
    raw, scored = session / "raw.jsonl", session / "scored.jsonl"
    raw.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    subprocess.run(
        [".venv-bfcl/bin/python", "scripts/score_bfcl.py", str(raw), str(scored)], check=True
    )
    rows = [json.loads(line) for line in scored.read_text().splitlines()]
    lookup = {(r["model"], r["condition"], r["item_id"]): r for r in rows}
    # A10 scoring is reused verbatim, including incorrect and truncated outputs.
    old_scored = {}
    for line in (source / "evaluation.jsonl").read_text().splitlines():
        r = json.loads(line)
        if r["model"] in names and r["temperature"] == 0:
            old_scored[r["model"], r["condition"], r["item_id"]] = r
    for condition in conditions:
        models, items, data = load(scored, condition=condition)
        report = analyze(models, items, data, ks=[1], seed=config["seed"], resamples=5000)
        report["scope"] = "Greedy, one outcome/item; only paired-item uncertainty is identified."
        save(session / ("analysis-" + condition.replace(":", "-") + ".json"), report)
    greedy = {}
    for arm in config["arms"]:
        greedy[arm] = {}
        for name in names:
            groups = [
                [lookup[name, f"{arm}:{run['run_id']}", item] for run in config["greedy_repeats"]]
                for item in ids
            ]
            changed = sum(len({r["output"] for r in group}) > 1 for group in groups)
            greedy[arm][name] = {
                "changed_text": changed,
                "changed_text_fraction": changed / 500,
                "changed_text_ci95": wilson(changed, 500),
                "changed_correctness": sum(len({r["passed"] for r in g}) > 1 for g in groups),
                "scores": {
                    run["run_id"]: float(np.mean([g[j]["passed"] for g in groups]))
                    for j, run in enumerate(config["greedy_repeats"])
                },
            }
    save(session / "greedy-summary.json", greedy)
    a10_greedy = json.loads((source / "greedy-summary.json").read_text())
    a10_pairs = json.loads((source / "pairwise-flips.json").read_text())
    pairs = []
    for index, (a, b) in enumerate(approval["pairs"]):
        if a not in names or b not in names:
            continue
        old = next(p for p in a10_pairs if {p["a"], p["b"]} == {a, b})
        result = {"a": a, "b": b, "a10": old["arms"], "l4": {}}
        for arm_index, arm in enumerate(config["arms"]):
            delta = [
                [
                    int(lookup[a, f"{arm}:{r['run_id']}", item]["passed"])
                    - int(lookup[b, f"{arm}:{r['run_id']}", item]["passed"])
                    for r in config["greedy_repeats"]
                ]
                for item in ids
            ]
            result["l4"][arm] = flip_summary(
                delta, seed=config["seed"] + 100 + index * 10 + arm_index
            )
        old_signs = np.sign(old["arms"]["default"]["observed_differences"]) * (
            1 if old["a"] == a else -1
        )
        new_signs = np.sign(result["l4"]["default"]["observed_differences"])
        result["default_strict_flip_reproduced"] = (
            bool(result["l4"]["default"]["observed_strict_flip"])
            if old["arms"]["default"]["observed_strict_flip"]
            else None
        )
        result["default_order_pattern_reproduced"] = bool(np.array_equal(old_signs, new_signs))
        pairs.append(result)
    save(session / "pairwise-gpu-comparison.json", pairs)
    agreement = []
    for name in names:
        for condition in conditions:
            cells = [
                (lookup[name, condition, item], old_scored[name, condition, item]) for item in ids
            ]
            agreement.append(
                {
                    "model": name,
                    "condition": condition,
                    "cross_gpu_text_changes": sum(a["output"] != b["output"] for a, b in cells),
                    "cross_gpu_correctness_changes": sum(
                        a["passed"] != b["passed"] for a, b in cells
                    ),
                    "items": 500,
                }
            )
    save(session / "cross-gpu-agreement.json", agreement)
    summary = {
        "status": "complete" if not missing else "incomplete",
        "models": names,
        "missing_models": missing,
        "predictions": len(rows),
        "gpu": "NVIDIA L4",
        "gpu_uuids": sorted({job["gpu_uuid"] for job in jobs}),
        "truncations": sum(r["finish_reason"] == "length" for r in rows),
        "error_types": dict(Counter(str(r.get("error_type")) for r in rows)),
        "raw_sha256": hashlib.sha256(raw.read_bytes()).hexdigest(),
        "scored_sha256": hashlib.sha256(scored.read_bytes()).hexdigest(),
    }
    save(session / "summary.json", summary)
    lines = [
        "# L4 follow-up alongside A10",
        "",
        f"Status: **{summary['status']}**. Completed {len(names)}/4 models and scored {len(rows):,} greedy predictions on the same 500 items, two arms, and batch sizes 1/8/32. Both pairs were selected before L4 outcomes. Missing models: {', '.join(missing) or 'none'}.",
        "",
    ]
    target = next((p for p in pairs if p["a"].startswith("meta-llama/")), None)
    if target:
        verdict = "reproduced" if target["default_strict_flip_reproduced"] else "did not reproduce"
        lines += [
            f"The A10 Llama3B/Qwen3-4B full-set strict batch flip **{verdict} on this L4**. Exact strict/tied order pattern across batch sizes reproduced: {target['default_order_pattern_reproduced']}. This is one physical L4 replication, not a statement about every L4 or serving schedule.",
            "",
        ]
    lines += [
        "## Full-set scores and bootstrap batch flips",
        "",
        "Score cells give correct calls out of 500 at batch sizes 1 / 8 / 32. A strict flip requires opposite strict orders at two batch settings; ties are separate. Bootstrap fractions use 5,000 paired item draws, with exploratory outer 95% intervals from 500 outer and 1,000 inner draws. Collapsed intervals do not prove population certainty. Monte Carlo precision and paired score-difference intervals are retained in JSON. Intervals are unadjusted for multiple comparisons.",
        "",
        "| Pair | GPU | Arm | Model A correct | Model B correct | Full-set strict flip | Bootstrap fraction [exploratory 95% interval] |",
        "|---|---|---|---|---|---|---|",
    ]
    for pair in pairs:
        for device, values in (("A10", a10_greedy), ("L4", greedy)):
            for arm in config["arms"]:
                counts = [
                    " / ".join(
                        str(round(values[arm][n]["scores"][r["run_id"]] * 500))
                        for r in config["greedy_repeats"]
                    )
                    for n in (pair["a"], pair["b"])
                ]
                stats = pair[device.lower()][arm]
                lines.append(
                    f"| {short(pair['a'])} vs {short(pair['b'])} | {device} | {arm} | {counts[0]} | {counts[1]} | {stats['observed_strict_flip']} | {pct(stats['estimate'])} {interval(stats['ci95'])} |"
                )
    lines += [
        "",
        "## Text changes across batch settings",
        "",
        "Wilson 95% intervals assume independent items. The same 500 items recur across models and GPUs; do not pool them as independent questions.",
        "",
        "| Model | GPU | Arm | Changed text / 500 | Rate [95% interval] | Changed correctness |",
        "|---|---|---|---:|---|---:|",
    ]
    for name in names:
        for device, values in (("A10", a10_greedy), ("L4", greedy)):
            for arm in config["arms"]:
                r = values[arm][name]
                lines.append(
                    f"| {short(name)} | {device} | {arm} | {r['changed_text']} | {pct(r['changed_text_fraction'])} {interval(r['changed_text_ci95'])} | {r['changed_correctness']} |"
                )
    lines += [
        "",
        "## Controls and interpretation",
        "",
        f"Validation matched every checkpoint revision, rendered/message hash, seed, inference package version, engine setting, and the Llama special-token correction with A10. Each process passed five smoke requests. The {len(names)} completed models and both arms shared the recorded L4 UUID. Incorrect and truncated outputs remain in the denominator. Cross-GPU exact-text and correctness agreement at fixed batch settings are saved separately.",
        "",
        f"Length-truncated outputs: {summary['truncations']}. No additional stochastic generation or repeated-throughput study was performed. A10's default process performed sampling before greedy evaluation; this focused follow-up starts greedy evaluation after smoke and the same per-condition warmup. Generation times support cost accounting; they are not a general performance comparison. The L4 worker requested and capped two CPU cores, versus the A10 worker's two-core request and four-core cap. Generation history, host/driver differences, and one card per family prevent attributing every difference solely to GPU architecture. The A10 close pairs were exploratory there; this L4 follow-up preselected them before collecting L4 data.",
        "",
        "## Cost and cleanup",
        "",
        f"Forecast ${receipt['forecast_usd']:.4f}; app-specific gross metering ${receipt['app_specific_gross_metered_usage_usd']:.4f}; conservative follow-up estimate ${receipt['estimated_spend_usd']:.4f}. Whole-project estimate ${receipt['project_estimate_usd']:.4f}/$12. The follow-up also has its own $5 cap. Metering is provisional and settled invoice actuals are unknown.",
        "",
        f"Owned apps stopped: {receipt['own_apps_stopped']}; owned running containers: {receipt['own_running_containers']}; active reservations: ${receipt['active_reservations_usd']:.2f}. Checkpoints were SHA256-verified before volume deletion when complete. qunti-check was not modified. See receipt.json, job-result.json budget gates, forecast.json, billing-tagged.json, and download-receipt.json.",
    ]
    (session / "REPORT.md").write_text("\n".join(lines) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
