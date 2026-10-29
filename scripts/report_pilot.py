"""Validate complete pilot artifacts, score comparisons, and render an honest report."""

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import subprocess

from evalnoise.cli import greedy
from evalnoise.data import load
from evalnoise.stats import analyze


def main():
    p = argparse.ArgumentParser()
    p.add_argument("session", type=Path)
    args = p.parse_args()
    config_path = args.session / "config.json"
    if not config_path.exists():
        config_path = Path("experiments/pilot.json")
    config = json.loads(config_path.read_text())
    manifest = json.loads(Path("experiments/subset.json").read_text())
    rows, metadata = [], []
    for name in config["models"]:
        artifact = args.session / (name.rsplit("/", 1)[-1] + ".json")
        result = json.loads(artifact.read_text())
        for arm in result["arms"]:
            rows.extend(arm["rows"])
            metadata.append(arm["metadata"])
    gpu_names = {r["gpu"] for r in metadata}
    if len(gpu_names) != 1:
        raise RuntimeError("pilot arms ran on different GPU types; do not pool their results")
    actual_gpu = next(iter(gpu_names))
    raw = args.session / "raw.jsonl"
    raw.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    scored = args.session / "scored.jsonl"
    subprocess.run(
        [".venv-bfcl/bin/python", "scripts/score_bfcl.py", str(raw), str(scored)], check=True
    )
    rows = [json.loads(r) for r in scored.read_text().splitlines()]
    cells = defaultdict(list)
    for r in rows:
        cells[(r["model"], r["condition"], r["item_id"])].append(r)
    conditions = ["sampling"] + [
        f"{arm}:{r['run_id']}" for arm in config["arms"] for r in config["greedy_repeats"]
    ]
    expected_keys = {
        (m, c, i) for m in config["models"] for c in conditions for i in manifest["pilot_ids"]
    }
    if set(cells) != expected_keys:
        raise RuntimeError("pilot incomplete: model/condition/item coverage differs from plan")
    for (_, condition, _), cell in cells.items():
        expected_n = config["n"] if condition == "sampling" else 1
        if len(cell) != expected_n or {r["sample_id"] for r in cell} != set(range(expected_n)):
            raise RuntimeError("pilot incomplete: missing or repeated samples")
    reports = {}
    for condition in conditions:
        models, items, data = load(scored, condition=condition)
        result = analyze(
            models,
            items,
            data,
            ks=[1, 5, 10] if condition == "sampling" else [1],
            resamples=5000,
            seed=config["seed"],
        )
        result["provenance"] = {
            "input_sha256": hashlib.sha256(scored.read_bytes()).hexdigest(),
            "condition": condition,
            "config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
        }
        path = args.session / ("analysis-" + condition.replace(":", "-") + ".json")
        path.write_text(json.dumps(result, indent=2) + "\n")
        reports[condition] = result
    lines = [
        "# Pilot report",
        "",
        "Measured pilot only: two checkpoints, 100 frozen items. Full experiment awaits approval.",
        f"GPU: **{actual_gpu}** for every model and arm. Batch-invariance findings are restricted to this GPU and pinned software/configuration.",
        "",
        "## Stochastic decoding",
        "",
        "Temperature 0.7; ten generations/item. Paired item-bootstrap 95% intervals.",
        "",
        "| Model | pass@1 | 95% CI | pass@5 | pass@10 |",
        "|---|---:|---|---:|---:|",
    ]
    sample = reports["sampling"]
    for model in sample["models"]:
        r = sample["metrics"]["pass@1"]["items"]["models"][model]
        p5 = sample["metrics"]["pass@5"]["items"]["models"][model]["estimate"]
        p10 = sample["metrics"]["pass@10"]["items"]["models"][model]["estimate"]
        lines.append(
            f"| {model} | {r['estimate']:.3f} | [{r['ci'][0]:.3f}, {r['ci'][1]:.3f}] | {p5:.3f} | {p10:.3f} |"
        )
    pair = sample["metrics"]["pass@1"]["items"]["pairwise"][0]
    lines += [
        "",
        f"Strict bootstrap P({pair['a']} > {pair['b']}) = {pair['p_a_beats_b']:.4f}; tie mass {pair['p_tie']:.4f}; rank-flip frequency {pair['rank_flip_frequency']}. These are stability fractions, not posterior probabilities.",
        "",
        "## Greedy batch intervention",
        "",
        "| Arm | Model | Changed exact text | Changed correctness | Changed token IDs |",
        "|---|---|---:|---:|---:|",
    ]
    plan = pair["planning"]
    if plan["status"] == "approximate_pilot_projection":
        lines[
            lines.index("## Greedy batch intervention") : lines.index(
                "## Greedy batch intervention"
            )
        ] = [
            f"Approximate pass@1 MDD at this design: **{plan['mdd_current_design']:.4f}** (fraction), two-sided alpha .05 and 80% power. This is a pilot-based projection, not a guaranteed detection threshold.",
            "",
            "| Samples/item/model | Items for a .05 target gap | MDD at current N |",
            "|---:|---:|---:|",
            *[
                f"| {r['samples_per_item_per_model']} | {r['items_for_target_gap']} | {r['mdd']:.4f} |"
                for r in plan["grid"]
            ],
            "",
        ]
    else:
        lines[
            lines.index("## Greedy batch intervention") : lines.index(
                "## Greedy batch intervention"
            )
        ] = [
            f"MDD projection unavailable: `{plan['status']}`. Observed boundary outcomes cannot establish zero uncertainty.",
            "",
        ]
    greedy_reports = {}
    for arm in config["arms"]:
        arm_rows = [r for r in rows if r["temperature"] == 0 and r["arm"] == arm]
        g = greedy(arm_rows)
        greedy_reports[arm] = g
        for model, r in g["models"].items():
            by_item = defaultdict(list)
            for row in arm_rows:
                if row["model"] == model:
                    by_item[row["item_id"]].append(row)
            token_changed = sum(
                len({tuple(x["token_ids"]) for x in cell}) > 1 for cell in by_item.values()
            )
            lines.append(
                f"| {arm} | {model} | {r['changed_fraction']:.1%} | {r['score_changed_fraction']:.1%} | {token_changed / len(by_item):.1%} |"
            )
    lines += [
        "",
        "| Arm | Batch size | Model A pass@1 | Model B pass@1 | A − B | Observed order |",
        "|---|---:|---:|---:|---:|---|",
    ]
    observed_orders = {}
    for arm in config["arms"]:
        signs = []
        for c in config["greedy_repeats"]:
            pair = reports[arm + ":" + c["run_id"]]["metrics"]["pass@1"]["items"]["pairwise"][0]
            d = pair["difference"]
            scores = reports[arm + ":" + c["run_id"]]["metrics"]["pass@1"]["items"]["models"]
            sign = 1 if d > 1e-12 else -1 if d < -1e-12 else 0
            signs.append(sign)
            order = pair["a"] + (" > " if sign > 0 else " < " if sign < 0 else " = ") + pair["b"]
            lines.append(
                f"| {arm} | {c['request_batch_size']} | {scores[pair['a']]['estimate']:.3f} | {scores[pair['b']]['estimate']:.3f} | {d:.3f} | {order} |"
            )
        observed_orders[arm] = signs
    for arm, signs in observed_orders.items():
        flipped = 1 in signs and -1 in signs
        lines += [
            "",
            f"{arm}: strict observed ranking reversal across batch configurations = **{flipped}**.",
            "",
        ]
    lines += [
        "## Warm throughput and startup",
        "",
        "| Model | Arm | Batch | Tokens/s | Completions/s | Decode seconds | Warmup seconds |",
        "|---|---|---|---:|---:|---:|---:|",
    ]
    rates = {}
    for meta in metadata:
        for t in meta["timings"]:
            lines.append(
                f"| {meta['model']['id']} | {meta['arm']} | {t['run_id']} | {t['generated_tokens_per_second']:.2f} | {t['completions_per_second']:.2f} | {t['elapsed_seconds']:.2f} | {t['warmup_seconds']:.2f} |"
            )
            rates[(meta["model"]["id"], meta["arm"], t["run_id"])] = t
    lines += [
        "",
        "| Model | Configuration | Fix/default tokens/s ratio | Fix/default completions/s ratio |",
        "|---|---|---:|---:|",
    ]
    for name in config["models"]:
        for c in config["greedy_repeats"]:
            base, fix = (
                rates[(name, "default", c["run_id"])],
                rates[(name, "batch_invariant", c["run_id"])],
            )
            lines.append(
                f"| {name} | {c['run_id']} | {fix['generated_tokens_per_second'] / base['generated_tokens_per_second']:.3f} | {fix['completions_per_second'] / base['completions_per_second']:.3f} |"
            )
    lines += [
        "",
        "Ratios below one indicate slower mitigation. Token throughput also depends on output length; inspect both rates. One timing per configuration and fixed baseline-first order cannot establish a precise general throughput penalty.",
        "",
    ]
    for meta in metadata:
        lines.append(
            f"- {meta['model']['id']} / {meta['arm']}: startup {meta['startup_seconds']:.2f}s, five smoke requests {meta['smoke_seconds']:.2f}s."
        )
    truncations = sum(r["finish_reason"] == "length" for r in rows)
    lines += [
        "",
        f"Length-truncated benchmark completions: {truncations}/{len(rows)}; retained and scored.",
        "",
        "## Data quality",
        "",
        "| Model | Condition | Predictions | Syntax/format failures | Truncated |",
        "|---|---|---:|---:|---:|",
    ]
    for model in config["models"]:
        for condition in conditions:
            group = [r for r in rows if r["model"] == model and r["condition"] == condition]
            malformed = sum(str(r.get("error_type", "")).startswith("ast_decoder:") for r in group)
            truncated = sum(r["finish_reason"] == "length" for r in group)
            lines.append(f"| {model} | {condition} | {len(group)} | {malformed} | {truncated} |")
    lines += [
        "",
        "## Cost and limitations",
        "",
        "See BUDGET.md and this session's billing snapshots. Gross metered-account change is not necessarily project-specific or settled. Reservations are not invoice actuals. No full-run launch is authorized by this report.",
        "",
        "Output disagreement need not imply score or rank disagreement. Absence of pilot flips does not prove batch invariance is unnecessary. Question dependence, small sample size, boundary bootstrap behavior and fixed arm order limit conclusions. No claim is made about other GPUs, training seeds, native tool APIs, or the complete BFCL leaderboard.",
    ]
    (args.session / "greedy-summary.json").write_text(
        json.dumps({"arms": greedy_reports, "observed_orders": observed_orders}, indent=2) + "\n"
    )
    report_path = args.session / "REPORT.md"
    report_path.write_text("\n".join(lines) + "\n")
    print(f"Validated {len(rows)} scored predictions; report: {report_path}")


if __name__ == "__main__":
    main()
