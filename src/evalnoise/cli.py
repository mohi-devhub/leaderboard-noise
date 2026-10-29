import argparse
import hashlib
import json
from pathlib import Path
import platform
import sys

import numpy as np

from . import __version__
from .data import load, read_rows
from .stats import analyze


def greedy(rows):
    groups = {}
    for r in rows:
        if r.get("temperature") != 0:
            raise ValueError("greedy rows must explicitly have temperature=0")
        if not isinstance(r.get("output"), str):
            raise ValueError("greedy rows need exact output text")
        key = r["model"], r["item_id"]
        runs = groups.setdefault(key, {})
        run = str(r["run_id"])
        if run in runs:
            raise ValueError("duplicate greedy run for item")
        runs[run] = r
    report = {}
    for model in sorted({k[0] for k in groups}):
        cells = [r for (m, _), r in groups.items() if m == model]
        run_sets = [set(r) for r in cells]
        if any(len(r) < 3 for r in cells) or any(r != run_sets[0] for r in run_sets):
            raise ValueError("greedy items need the same set of at least three runs")
        changed = sum(len({r["output"] for r in runs.values()}) > 1 for runs in cells)
        scored = all("passed" in r for runs in cells for r in runs.values())
        report[model] = {
            "n_items": len(cells),
            "n_runs": len(run_sets[0]),
            "changed_items": changed,
            "changed_fraction": changed / len(cells),
            "score_changed_fraction": (
                sum(len({r["passed"] for r in runs.values()}) > 1 for runs in cells) / len(cells)
            )
            if scored
            else None,
        }
    return {"comparison": "exact decoded output text across all runs", "models": report}


def main(argv=None):
    parser = argparse.ArgumentParser(prog="evalnoise")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("analyze", help="Analyze aligned binary per-item results")
    p.add_argument("input", type=Path)
    p.add_argument("--k", type=int, nargs="+", default=[1])
    p.add_argument("--resamples", type=int, default=5000)
    p.add_argument("--seed", type=int, default=20261101)
    p.add_argument("--confidence", type=float, default=0.95)
    p.add_argument("--gap", type=float, default=0.05, help="target pass@1 gap as a fraction")
    p.add_argument("--alpha", type=float, default=0.05)
    p.add_argument("--power", type=float, default=0.8)
    p.add_argument("--sample-grid", type=int, nargs="+", default=[1, 3, 5, 10, 20])
    for key, default in (
        ("model", "model"),
        ("item", "item_id"),
        ("score", "passed"),
        ("sample", "sample_id"),
    ):
        p.add_argument(f"--{key}-key", default=default)
    p.add_argument("--benchmark")
    p.add_argument("--condition")
    g = sub.add_parser("greedy", help="Measure exact-output disagreement across greedy runs")
    g.add_argument("input", type=Path)
    for command in (p, g):
        command.add_argument("--output", type=Path, help="write complete JSON report")
        command.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args(argv)
    try:
        if args.command == "analyze":
            models, items, data = load(
                args.input,
                args.model_key,
                args.item_key,
                args.score_key,
                args.sample_key,
                args.benchmark,
                args.condition,
            )
            result = analyze(
                models,
                items,
                data,
                ks=args.k,
                resamples=args.resamples,
                seed=args.seed,
                confidence=args.confidence,
                gap=args.gap,
                alpha=args.alpha,
                power=args.power,
                sample_grid=args.sample_grid,
            )
        else:
            result = greedy(read_rows(args.input))
        result["provenance"] = {
            "input_sha256": hashlib.sha256(args.input.read_bytes()).hexdigest(),
            "evalnoise": __version__,
            "python": platform.python_version(),
            "numpy": np.__version__,
        }
        rendered = json.dumps(result, indent=2, allow_nan=False) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered)
        if args.format == "json":
            print(rendered, end="")
        elif args.command == "greedy":
            for name, r in result["models"].items():
                print(
                    f"{name}: {r['changed_items']}/{r['n_items']} outputs changed ({r['changed_fraction']:.1%})"
                )
        else:
            print(f"{result['n_items']} paired items; {args.resamples} resamples; seed={args.seed}")
            for metric, modes in result["metrics"].items():
                for mode, report in modes.items():
                    label = (
                        "empirical resampling range; diagnostic"
                        if mode == "sampling" and metric != "pass@1"
                        else f"{args.confidence:.0%} CI"
                    )
                    print(f"\n{metric} — {mode} uncertainty ({label})")
                    for name, row in report["models"].items():
                        print(
                            f"  {name}: {row['estimate']:.4f} [{row['ci'][0]:.4f}, {row['ci'][1]:.4f}]"
                        )
                    print("  A vs B | P(A>B) | P(tie) | rank flip | difference CI")
                    for row in report["pairwise"]:
                        flip = (
                            "undefined (observed tie)"
                            if row["rank_flip_frequency"] is None
                            else f"{row['rank_flip_frequency']:.3f}"
                        )
                        print(
                            f"  {row['a']} vs {row['b']} | {row['p_a_beats_b']:.3f} | {row['p_tie']:.3f} | {flip} | {row['ci']}"
                        )
                        if "planning" in row:
                            plan = row["planning"]
                            print(f"    planning: {plan['status']}")
                            if "mdd_current_design" in plan:
                                print(
                                    f"    MDD={plan['mdd_current_design']:.4f}; minimum samples/item at N={result['n_items']}: {plan['minimum_samples_at_current_items']}"
                                )
                                for entry in plan["grid"]:
                                    print(
                                        f"    m={entry['samples_per_item_per_model']}: N={entry['items_for_target_gap']} for gap={args.gap}"
                                    )
            for warning in result["warnings"]:
                print(f"Note: {warning}")
        return 0
    except (ValueError, KeyError, OSError, TypeError) as exc:
        print(f"evalnoise: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
