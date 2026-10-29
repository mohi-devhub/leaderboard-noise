"""Validate and score the complete study, retaining timing rows outside accuracy analysis."""

import argparse
from collections import defaultdict
import csv
import hashlib
from itertools import combinations
import json
from pathlib import Path
import subprocess

import numpy as np

from evalnoise.data import load
from evalnoise.stats import analyze, planning
from study_analysis import flip_summary, wilson


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def short(name):
    return name.rsplit("/", 1)[-1]


def pct(value):
    return "undefined" if value is None else f"{value:.2%}"


def bounds(values):
    return "undefined" if values is None else f"[{values[0]:.2%}, {values[1]:.2%}]"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("session", type=Path)
    args = parser.parse_args()
    session = args.session
    config = json.loads((session / "config.json").read_text())
    manifest = json.loads(Path("experiments/subset.json").read_text())
    models = json.loads((session / "models.json").read_text())
    names = [m["id"] for m in models]
    conditions = ["sampling"] + [
        f"{arm}:{run['run_id']}" for arm in config["arms"] for run in config["greedy_repeats"]
    ]
    timing_conditions = [
        f"timing:{arm}:repeat{repeat}:{run['run_id']}"
        for repeat in range(config["timing_repetitions"])
        for arm in config["arms"]
        for run in config["greedy_repeats"]
    ]
    rows, metadata, jobs = [], [], []
    for name in names:
        job = json.loads((session / (short(name) + ".json")).read_text())
        if job["status"] != "complete":
            raise RuntimeError("cannot report an incomplete model as a completed study")
        jobs.append(job)
        for arm in job["arms"]:
            rows.extend(arm["rows"])
            metadata.append(arm["metadata"])
    gpus = {job["gpu"] for job in jobs}
    uuids = {job["gpu_uuid"] for job in jobs}
    if not gpus.issubset({"NVIDIA A10", "NVIDIA A10G"}) or len(uuids) > 2:
        raise RuntimeError("GPU tier or approved two-device recovery protocol changed")
    if len({job["gpu_uuid"] for job in jobs[1:]}) != 1:
        raise RuntimeError("remaining models did not share their allocated A10")
    gpu = next(iter(gpus)) if len(gpus) == 1 else "Modal A10 tier (A10 and A10G)"
    device_by_model = {job["model"]: job["gpu"] for job in jobs}
    prompt_hashes = defaultdict(set)
    seed_bases = defaultdict(set)
    for row in rows:
        key = row["model"], row["item_id"]
        prompt_hashes[key].add(row["rendered_prompt_sha256"])
        seed_bases[key].add(row["sampling_seed"] - row["sample_id"])
        if row["gpu"] != device_by_model[row["model"]]:
            raise RuntimeError("row GPU differs from recorded device")
    if any(len(values) != 1 for values in prompt_hashes.values()):
        raise RuntimeError("rendered prompts changed across arms, batches, or repetitions")
    if any(len(values) != 1 for values in seed_bases.values()):
        raise RuntimeError("seed allocation changed across arms, batches, or repetitions")
    expected_engine = {
        "enforce_eager": True,
        "enable_prefix_caching": False,
        "max_num_seqs": 64,
        "dtype": "bfloat16",
    }
    if any(
        meta["engine"] != expected_engine or meta["packages"].get("vllm") != "0.32.0"
        for meta in metadata
    ):
        raise RuntimeError("inference settings or pinned vLLM changed")
    for meta in metadata:
        if meta["model"]["id"] == "meta-llama/Llama-3.2-3B-Instruct" and meta.get(
            "tokenization_kwargs"
        ) != {"add_special_tokens": False}:
            raise RuntimeError("Llama rendered prompts must not receive an extra BOS token")
    expected = {
        (name, condition, item)
        for name in names
        for condition in conditions
        for item in manifest["full_ids"]
    } | {
        (name, condition, item)
        for name in names
        for condition in timing_conditions
        for item in manifest["pilot_ids"]
    }
    cells = defaultdict(list)
    for row in rows:
        cells[(row["model"], row["condition"], row["item_id"])].append(row)
    if set(cells) != expected:
        raise RuntimeError("missing or unexpected model/condition/item cells")
    for (_, condition, _), cell in cells.items():
        count = config["n"] if condition == "sampling" else 1
        if len(cell) != count or {r["sample_id"] for r in cell} != set(range(count)):
            raise RuntimeError("missing or duplicated predictions")
    raw = session / "raw.jsonl"
    raw.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))
    scored = session / "scored.jsonl"
    subprocess.run(
        [".venv-bfcl/bin/python", "scripts/score_bfcl.py", str(raw), str(scored)], check=True
    )
    rows = [json.loads(line) for line in scored.read_text().splitlines()]
    primary = [r for r in rows if r["phase"] == "evaluation"]
    primary_path = session / "evaluation.jsonl"
    primary_path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in primary))
    by_cell = {
        (r["model"], r["condition"], r["item_id"]): r for r in primary if r["temperature"] == 0
    }
    analysis = {}
    for condition in conditions:
        ms, ids, data = load(primary_path, condition=condition)
        report = analyze(
            ms,
            ids,
            data,
            ks=[1, 5, 10] if condition == "sampling" else [1],
            seed=config["seed"],
            resamples=5000,
        )
        report["provenance"] = {
            "input_sha256": hashlib.sha256(primary_path.read_bytes()).hexdigest(),
            "condition": condition,
            "config_sha256": hashlib.sha256((session / "config.json").read_bytes()).hexdigest(),
        }
        save(session / ("analysis-" + condition.replace(":", "-") + ".json"), report)
        analysis[condition] = report
    ordered_ids = manifest["full_ids"]
    greedy = {}
    for arm in config["arms"]:
        greedy[arm] = {}
        for name in names:
            groups = [
                [by_cell[name, f"{arm}:{run['run_id']}", item] for run in config["greedy_repeats"]]
                for item in ordered_ids
            ]
            changed_text = sum(len({r["output"] for r in group}) > 1 for group in groups)
            changed_tokens = sum(
                len({tuple(r["token_ids"]) for r in group}) > 1 for group in groups
            )
            changed_scores = sum(len({r["passed"] for r in group}) > 1 for group in groups)
            greedy[arm][name] = {
                "n_items": len(groups),
                "changed_text": changed_text,
                "changed_text_fraction": changed_text / len(groups),
                "changed_text_ci95": wilson(changed_text, len(groups)),
                "changed_tokens": changed_tokens,
                "changed_correctness": changed_scores,
                "scores": {
                    run["run_id"]: float(np.mean([g[j]["passed"] for g in groups]))
                    for j, run in enumerate(config["greedy_repeats"])
                },
            }
    save(session / "greedy-summary.json", greedy)
    sample_means = defaultdict(dict)
    samples = defaultdict(list)
    for r in primary:
        if r["condition"] == "sampling":
            samples[r["model"], r["item_id"]].append(r["passed"])
    for name in names:
        for item in ordered_ids:
            sample_means[name][item] = np.mean(samples[name, item])
    preselected = {frozenset(pair) for pair in config["published_close_pairs"]}
    job_by_model = {job["model"]: job for job in jobs}
    pairs = []
    for pair_index, (a, b) in enumerate(combinations(names, 2)):
        serial_gap = (
            greedy["default"][a]["scores"]["serial"] - greedy["default"][b]["scores"]["serial"]
        )
        pair = {
            "a": a,
            "b": b,
            "preselected_from_published_scores": frozenset((a, b)) in preselected,
            "observed_close": abs(serial_gap) <= config["close_gap"] + 1e-12,
            "default_serial_gap": serial_gap,
            "same_physical_gpu": job_by_model[a]["gpu_uuid"] == job_by_model[b]["gpu_uuid"],
            "planning_gap_3pp": planning(
                [np.array(samples[a, item], dtype=float) for item in ordered_ids],
                [np.array(samples[b, item], dtype=float) for item in ordered_ids],
                0.03,
                0.05,
                0.8,
                [1, 3, 5, 10, 20],
            ),
            "sampling": flip_summary(
                [sample_means[a][i] - sample_means[b][i] for i in ordered_ids],
                seed=config["seed"] + pair_index * 10,
                kind="sampling",
            ),
            "arms": {},
        }
        for arm_index, arm in enumerate(config["arms"]):
            differences = [
                [
                    int(by_cell[a, f"{arm}:{run['run_id']}", item]["passed"])
                    - int(by_cell[b, f"{arm}:{run['run_id']}", item]["passed"])
                    for run in config["greedy_repeats"]
                ]
                for item in ordered_ids
            ]
            pair["arms"][arm] = flip_summary(
                differences, seed=config["seed"] + pair_index * 10 + arm_index + 1
            )
        pair["mitigation_order_changes"] = {}
        for index, run in enumerate(config["greedy_repeats"]):
            default_gap = pair["arms"]["default"]["observed_differences"][index]
            fixed_gap = pair["arms"]["batch_invariant"]["observed_differences"][index]
            pair["mitigation_order_changes"][run["run_id"]] = {
                "default_gap": default_gap,
                "invariant_gap": fixed_gap,
                "strict_reversal": default_gap * fixed_gap < -1e-12,
                "one_or_both_tied": abs(default_gap) <= 1e-12 or abs(fixed_gap) <= 1e-12,
            }
        pairs.append(pair)
    save(session / "pairwise-flips.json", pairs)
    with (session / "pairwise-flips.csv").open("w") as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                "model_a",
                "model_b",
                "preselected",
                "observed_close",
                "arm",
                "observed_flip",
                "bootstrap_flip_fraction",
                "outer_ci95_low",
                "outer_ci95_high",
                "mc_ci95_low",
                "mc_ci95_high",
            ]
        )
        for p in pairs:
            for arm, r in p["arms"].items():
                writer.writerow(
                    [
                        p["a"],
                        p["b"],
                        p["preselected_from_published_scores"],
                        p["observed_close"],
                        arm,
                        r["observed_strict_flip"],
                        r["estimate"],
                        *r["ci95"],
                        *r["mc_wilson95"],
                    ]
                )
    timings = defaultdict(dict)
    for meta in metadata:
        for timing in meta["timings"]:
            if timing["phase"] != "timing":
                continue
            key = meta["model"]["id"], meta["arm"], timing["run_id"]
            repeat = timing["repeat_index"]
            if repeat in timings[key]:
                raise RuntimeError("duplicate throughput repetition")
            timings[key][repeat] = timing
    throughput = []
    for name in names:
        for run in config["greedy_repeats"]:
            label = run["run_id"]
            baseline, invariant = (
                timings[name, "default", label],
                timings[name, "batch_invariant", label],
            )
            if set(baseline) != set(range(3)) or set(invariant) != set(range(3)):
                raise RuntimeError("need three paired timing repetitions")
            token_ratios = [
                invariant[i]["generated_tokens_per_second"]
                / baseline[i]["generated_tokens_per_second"]
                for i in range(3)
            ]
            completion_ratios = [
                invariant[i]["completions_per_second"] / baseline[i]["completions_per_second"]
                for i in range(3)
            ]
            throughput.append(
                {
                    "model": name,
                    "configuration": label,
                    "baseline": list(baseline.values()),
                    "invariant": list(invariant.values()),
                    "token_rate_ratios": token_ratios,
                    "token_rate_ratio_median": float(np.median(token_ratios)),
                    "token_rate_ratio_range": [min(token_ratios), max(token_ratios)],
                    "completion_rate_ratios": completion_ratios,
                    "completion_rate_ratio_median": float(np.median(completion_ratios)),
                    "completion_rate_ratio_range": [min(completion_ratios), max(completion_ratios)],
                    "elapsed_time_ratios": [
                        invariant[i]["elapsed_seconds"] / baseline[i]["elapsed_seconds"]
                        for i in range(3)
                    ],
                }
            )
    save(session / "throughput-summary.json", throughput)
    timing_consistency = []
    timed_rows = [r for r in rows if r["phase"] == "timing"]
    for name in names:
        for arm in config["arms"]:
            for run in config["greedy_repeats"]:
                groups = defaultdict(list)
                for r in timed_rows:
                    if r["model"] == name and r["arm"] == arm and r["run_id"] == run["run_id"]:
                        groups[r["item_id"]].append(r)
                timing_consistency.append(
                    {
                        "model": name,
                        "arm": arm,
                        "configuration": run["run_id"],
                        "items": len(groups),
                        "changed_text_across_repetitions": sum(
                            len({r["output"] for r in g}) > 1 for g in groups.values()
                        ),
                    }
                )
    save(session / "timing-repeat-consistency.json", timing_consistency)
    summary = {
        "gpu": gpu,
        "gpu_uuids": sorted(uuids),
        "gpu_names": sorted(gpus),
        "gpu_name_by_model": device_by_model,
        "gpu_uuid_by_model": {job["model"]: job["gpu_uuid"] for job in jobs},
        "models": names,
        "primary_predictions": len(primary),
        "timing_predictions": len(timed_rows),
        "total_predictions": len(rows),
        "truncated": sum(r["finish_reason"] == "length" for r in rows),
        "syntax_failures": sum(
            str(r.get("error_type", "")).startswith("ast_decoder:") for r in rows
        ),
        "observed_close_pairs": sum(p["observed_close"] for p in pairs),
        "preselected_close_pairs": 3,
        "observed_close_pairs_same_gpu": sum(
            p["observed_close"] and p["same_physical_gpu"] for p in pairs
        ),
        "pairs_with_mitigation_order_change": sum(
            any(change["strict_reversal"] for change in pair["mitigation_order_changes"].values())
            for pair in pairs
        ),
    }
    save(session / "summary.json", summary)
    lines = [
        "# Six-model BFCL study",
        "",
        f"Completed evaluation on **{gpu}**. The preserved first model used one device; the remaining five shared a second device after the infrastructure interruption. Every model's two arms and timing repetitions stayed on its assigned GPU. Exact names and UUIDs are in summary.json; conclusions are restricted to this recorded A10 setup. {len(primary):,} primary predictions and {len(timed_rows):,} separate timing predictions were scored with the official BFCL harness.",
        "",
        "## Selection rationale",
        "",
        "The user approved a new roster targeting close scores. The pilot's 32-point Qwen0.5B/1.5B sampling gap excluded 0.5B. Qwen1.5B remains the measured anchor, joined by Qwen2.5-3B, Qwen3-1.7B, Llama3.2-3B, xLAM2-3B, and Qwen3-4B-Instruct-2507. Published non-live AST scores preselected Qwen3-1.7B/Llama3B/xLAM3B, with gaps 0.25/0.04/0.29 points. Their published FC scores guide selection but do not reproduce this common-prompting Python subset. No model or item was replaced after full-study results. [Frozen plan](../../docs/FULL_STUDY_PLAN.md), [official leaderboard source](https://gorilla.cs.berkeley.edu/data_overall.csv).",
        "",
        f"Observed default-serial gaps at most three points: **{summary['observed_close_pairs']}/15 pairs**. Preselected pairs remain reported even when not close on this task. Additional close-pair labels are exploratory selection on these data.",
        "",
        "## Sampling accuracy",
        "",
        "Temperature .7, n=10; 500 paired items, 5,000 item-bootstrap resamples. Timing repetitions do not increase this sample count.",
        "",
        "| Model | pass@1 | 95% item CI | pass@5 | pass@10 |",
        "|---|---:|---|---:|---:|",
    ]
    sample = analysis["sampling"]
    for name in names:
        stats = sample["metrics"]["pass@1"]["items"]["models"][name]
        p5 = sample["metrics"]["pass@5"]["items"]["models"][name]["estimate"]
        p10 = sample["metrics"]["pass@10"]["items"]["models"][name]["estimate"]
        lines.append(
            f"| {short(name)} | {pct(stats['estimate'])} | {bounds(stats['ci'])} | {pct(p5)} | {pct(p10)} |"
        )
    lines += [
        "",
        "## Pairwise flip rates and uncertainty",
        "",
        "A batch flip means at least two batch settings give opposite strict orders in the same paired item resample. Ties are separate and do not count as flips. The fraction concerns resampling stability, not a posterior probability. Sampling flips reverse the fixed observed sampling order.",
        "",
        "Intervals below are exploratory outer item-bootstrap percentile ranges, with 500 outer and 1,000 inner draws. They can collapse at ties/boundaries and with absent empirical patterns, and include inner Monte Carlo error. They are not simultaneous or guaranteed-calibrated population intervals. Separate Wilson intervals in JSON quantify only finite Monte Carlo precision conditional on these observed data. Inspect paired score-difference CIs alongside flip fractions.",
        "",
        "| Pair | Preselected / observed close | Arm | Actual full-set batch flip | Bootstrap flip fraction | Exploratory 95% interval |",
        "|---|---|---|---|---:|---|",
    ]
    for p in pairs:
        if not (p["observed_close"] or p["preselected_from_published_scores"]):
            continue
        tag = f"{p['preselected_from_published_scores']} / {p['observed_close']}"
        for arm, r in p["arms"].items():
            lines.append(
                f"| {short(p['a'])} vs {short(p['b'])} | {tag} | {arm} | {r['observed_strict_flip']} | {pct(r['estimate'])} | {bounds(r['ci95'])} |"
            )
        r = p["sampling"]
        lines.append(
            f"| {short(p['a'])} vs {short(p['b'])} | {tag} | sampling | n/a | {pct(r['estimate'])} | {bounds(r['ci95'])} |"
        )
    lines += [
        "",
        "All 15 comparisons, including non-close pairs, are in [pairwise-flips.json](pairwise-flips.json) and [CSV](pairwise-flips.csv). Complete score-difference intervals, bootstrap win/tie fractions, rank distributions, and MDD/item/sample projections are in the condition-specific analysis JSON files.",
        "",
        "| Pair, A minus B | Default serial gap | Paired item-bootstrap 95% gap CI | Same physical A10 |",
        "|---|---:|---|---|",
    ]
    for p in pairs:
        if p["observed_close"] or p["preselected_from_published_scores"]:
            r = p["arms"]["default"]
            lines.append(
                f"| {short(p['a'])} vs {short(p['b'])} | {pct(p['default_serial_gap'])} | {bounds(r['difference_ci95'][0])} | {p['same_physical_gpu']} |"
            )
    lines += [
        "",
        "## Planning for a three-point gap",
        "",
        "Normal-approximation projections use the stochastic pass@1 paired variance components, two-sided alpha .05, and 80% power. They assume independent questions and iid model generations. They are planning estimates, not guarantees of significance for another evaluation or pair.",
        "",
        "| Pair | Current MDD, 500 items × 10 samples/model | Projected items for a .03 gap at 10 samples/model |",
        "|---|---:|---:|",
    ]
    for p in pairs:
        if not (p["observed_close"] or p["preselected_from_published_scores"]):
            continue
        plan = p["planning_gap_3pp"]
        if plan["status"] == "approximate_pilot_projection":
            required = next(
                g["items_for_target_gap"]
                for g in plan["grid"]
                if g["samples_per_item_per_model"] == 10
            )
            lines.append(
                f"| {short(p['a'])} vs {short(p['b'])} | {pct(plan['mdd_current_design'])} | {required} |"
            )
        else:
            lines.append(
                f"| {short(p['a'])} vs {short(p['b'])} | unidentified | {plan['status']} |"
            )
    lines += [
        "",
        "## Greedy changes",
        "",
        "| Model | Arm | Changed text / 500 | Wilson 95% interval | Changed token IDs | Changed correctness | Scores at batches 1 / 8 / 32 |",
        "|---|---|---:|---|---:|---:|---|",
    ]
    for name in names:
        for arm in config["arms"]:
            r = greedy[arm][name]
            scores = " / ".join(pct(r["scores"][run["run_id"]]) for run in config["greedy_repeats"])
            lines.append(
                f"| {short(name)} | {arm} | {r['changed_text']} | {bounds(r['changed_text_ci95'])} | {r['changed_tokens']} | {r['changed_correctness']} | {scores} |"
            )
    lines += [
        "",
        "Wilson intervals assume independent items; shared functions/templates can violate that assumption. Repeat-to-repeat timing output checks are saved separately. Stabilizing text does not imply improved accuracy.",
        "",
        f"Changing the mitigation setting itself strictly reversed {summary['pairs_with_mitigation_order_change']} pairwise full-set orders at one or more fixed batch sizes. This is separate from batch-induced instability within an arm. Details, including transitions involving ties, are in each pair's `mitigation_order_changes` field.",
        "",
        "## Repeated throughput",
        "",
        "Three matched repetitions use the same 100 items in each configuration, alternating arm order between repetitions. Values are fix/default ratios. Ratios below one mean lower invariant throughput. Output length affects tokens/s, so completions/s and elapsed-time ratios are also retained. Initialization and warmup are excluded here but included in cost.",
        "",
        "| Model | Batch configuration | Median token-rate ratio | Range, three repetitions | Median completion-rate ratio | Completion-rate range |",
        "|---|---|---:|---|---:|---|",
    ]
    for r in throughput:
        lo, hi = r["token_rate_ratio_range"]
        clo, chi = r["completion_rate_ratio_range"]
        lines.append(
            f"| {short(r['model'])} | {r['configuration']} | {r['token_rate_ratio_median']:.3f} | [{lo:.3f}, {hi:.3f}] | {r['completion_rate_ratio_median']:.3f} | [{clo:.3f}, {chi:.3f}] |"
        )
    lines += [
        "",
        "These are measured configuration overheads with three repetitions, not a general performance recommendation. No limiter profile or production tuning study was conducted. Full timings, generated-token counts, completion counts, driver, host load, and installed versions are retained in model artifacts.",
        "",
        "## Data quality and scope",
        "",
        f"Total scored: {len(rows):,}; length-truncated: {summary['truncated']}; AST syntax/format failures: {summary['syntax_failures']}. Every planned cell was validated. Incorrect and truncated model outputs remain in the denominator. Timing rows are scored to detect fast failures but do not enter primary accuracy or rank calculations.",
        "",
        "This is the frozen Python single-turn subset, not the official overall leaderboard. Findings concern greedy batching on this GPU, pinned software, common prompts, and fixed decoding limits. They do not cover training-seed sensitivity, other GPUs, native tool APIs, code execution, or all possible serving schedules. Intervals are exploratory and unadjusted for multiple comparisons. Null results are retained.",
        "",
        "## Cost and shutdown",
        "",
        "See receipt.json, budget-checks.json, forecast.json, and BUDGET.md for measured resource time versus forecast, metering attribution, reservations, and invoice status. Account-wide deltas include unrelated qunti-check use and are not project costs. Cleanup targets only evalnoise. The prior pilot ran on a separately recorded GPU and is not pooled with this experiment.",
    ]
    (session / "REPORT.md").write_text("\n".join(lines) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
