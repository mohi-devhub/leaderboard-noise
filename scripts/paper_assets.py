"""Render paper tables/figures from frozen summaries. Never generate, grade, or resample answers."""

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

A10 = Path("results/study-20261028T065939Z")
L4 = Path("results/l4-continuation-20261028T224638Z")
BATCHES = ("serial", "batch8", "batch32")
ARMS = ("default", "batch_invariant")
LABELS = {
    "Qwen2.5-1.5B-Instruct": "Qwen2.5-1.5B",
    "Qwen2.5-3B-Instruct": "Qwen2.5-3B",
    "Qwen3-1.7B": "Qwen3-1.7B",
    "Llama-3.2-3B-Instruct": "Llama3.2-3B",
    "xLAM-2-3b-fc-r": "xLAM2-3B",
    "Qwen3-4B-Instruct-2507": "Qwen3-4B",
}


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def label(name):
    return LABELS[name.rsplit("/", 1)[-1]]


def esc(value):
    return str(value).replace("_", r"\_").replace("%", r"\%").replace("&", r"\&")


def load(root):
    files = {
        "a_summary": A10 / "summary.json",
        "a_receipt": A10 / "receipt.json",
        "a_greedy": A10 / "greedy-summary.json",
        "a_pairs": A10 / "pairwise-flips.json",
        "timing": A10 / "throughput-summary.json",
        "sampling": A10 / "analysis-sampling.json",
        "l_summary": L4 / "summary.json",
        "l_receipt": L4 / "receipt.json",
        "l_greedy": L4 / "greedy-summary.json",
        "pairs": L4 / "pairwise-gpu-comparison.json",
        "agreement": L4 / "cross-gpu-agreement.json",
        "config": Path("experiments/full-study.json"),
        "subset": Path("experiments/subset.json"),
        "roster": Path("experiments/full-models.json"),
    }
    data = {k: read(root / p) for k, p in files.items()}
    assert (
        data["a_summary"]["total_predictions"] == 58800
        and data["l_summary"]["predictions"] == 12000
    )
    assert data["l_summary"]["status"] == "complete"
    data["files"] = files
    return data


def tabular(path, columns, headers, rows):
    body = [
        r"\begin{tabular}{" + columns + "}",
        r"\toprule",
        " & ".join(headers) + r" \\",
        r"\midrule",
    ]
    body += [" & ".join(map(str, row)) + r" \\" for row in rows]
    body += [r"\bottomrule", r"\end{tabular}"]
    path.write_text("\n".join(body) + "\n")


def build(root):
    d = load(root)
    out = root / "paper"
    (out / "tables").mkdir(parents=True, exist_ok=True)
    numbers = {}

    def macro(key, value, source, rendered=None):
        numbers[key] = {
            "value": value,
            "source": source,
            "tex": str(value) if rendered is None else rendered,
        }

    default_rates = [
        r["changed_text_fraction"]
        for k in ("a_greedy", "l_greedy")
        for r in d[k]["default"].values()
    ]
    ratios = [r["token_rate_ratio_median"] for r in d["timing"]]
    target = next(p for p in d["pairs"] if p["a"].startswith("meta-llama/"))
    close = [p for p in d["a_pairs"] if p["observed_close"]]
    llama = next(p for p in close if p["a"].startswith("meta-llama/"))
    qwen = next(p for p in close if p["a"].startswith("Qwen/"))
    macro("NItems", len(d["subset"]["full_ids"]), "subset.full_ids")
    macro("NAtenModels", len(d["a_summary"]["models"]), "a_summary.models")
    macro("NLfourModels", len(d["l_summary"]["models"]), "l_summary.models")
    macro("NSamples", d["config"]["n"], "config.n")
    macro(
        "AtenCount",
        d["a_summary"]["total_predictions"],
        "a_summary.total_predictions",
        f"{d['a_summary']['total_predictions']:,}",
    )
    macro(
        "LfourCount",
        d["l_summary"]["predictions"],
        "l_summary.predictions",
        f"{d['l_summary']['predictions']:,}",
    )
    macro(
        "TotalCount",
        d["a_summary"]["total_predictions"] + d["l_summary"]["predictions"],
        "a_summary + l_summary",
        f"{d['a_summary']['total_predictions'] + d['l_summary']['predictions']:,}",
    )
    macro(
        "TimingCount",
        d["a_summary"]["timing_predictions"],
        "a_summary.timing_predictions",
        f"{d['a_summary']['timing_predictions']:,}",
    )
    macro(
        "TextRounded",
        [min(default_rates), max(default_rates)],
        "a_greedy/l_greedy.default.changed_text_fraction",
        f"{math.floor(min(default_rates) * 100)}--{math.ceil(max(default_rates) * 100)}\\%",
    )
    macro(
        "TextExact",
        [min(default_rates), max(default_rates)],
        "a_greedy/l_greedy.default.changed_text_fraction",
        f"{min(default_rates):.1%}--{max(default_rates):.1%}".replace("%", r"\%"),
    )
    macro(
        "ThroughputLoss",
        [1 - max(ratios), 1 - min(ratios)],
        "timing.token_rate_ratio_median",
        f"{round(100 * (1 - max(ratios)))}--{round(100 * (1 - min(ratios)))}\\%",
    )
    macro(
        "TokenRatioRange",
        [min(ratios), max(ratios)],
        "timing.token_rate_ratio_median",
        f"{min(ratios):.3f}--{max(ratios):.3f}",
    )
    macro("RootSeed", d["config"]["seed"], "config.seed")
    macro("BFCLVersion", d["subset"]["bfcl_version"], "subset.bfcl_version")
    macro("MaxTokens", d["config"]["max_tokens"], "config.max_tokens")
    macro("ContextLimit", d["config"]["max_model_len"], "config.max_model_len")
    macro("SampleTemperature", d["config"]["temperature"], "config.temperature")
    macro("TimingItems", d["config"]["timing_items"], "config.timing_items")
    macro("TimingRepetitions", d["config"]["timing_repetitions"], "config.timing_repetitions")
    macro(
        "BootstrapCount",
        target["l4"]["default"]["resamples"],
        "pairs.l4.default.resamples",
        "5,000",
    )
    macro(
        "OuterCount", target["l4"]["default"]["outer_resamples"], "pairs.l4.default.outer_resamples"
    )
    macro(
        "InnerCount",
        target["l4"]["default"]["inner_resamples"],
        "pairs.l4.default.inner_resamples",
        "1,000",
    )
    macro(
        "OneItemGap",
        abs(target["a10"]["default"]["observed_differences"][0]) * 100,
        "pairs.a10.default.observed_differences[0]",
        "0.2",
    )
    halfwidth = max(
        (c[1] - c[0]) * 50
        for gpu in ("a10", "l4")
        for c in target[gpu]["default"]["difference_ci95"]
    )
    macro(
        "PairedHalfWidth",
        round(halfwidth),
        "pairs.*.default.difference_ci95 (rounded half-width)",
        str(round(halfwidth)),
    )
    endpoint = max(
        abs(x) * 100
        for gpu in ("a10", "l4")
        for c in target[gpu]["default"]["difference_ci95"]
        for x in c
    )
    macro("PairedEndpoint", endpoint, "pairs.a10/l4.default.difference_ci95", f"{endpoint:.1f}")
    for k, p in [("Llama", llama), ("Qwen", qwen)]:
        plan = p["planning_gap_3pp"]
        n = next(
            x["items_for_target_gap"] for x in plan["grid"] if x["samples_per_item_per_model"] == 10
        )
        macro("Items" + k, n, "a_pairs.planning_gap_3pp.grid[10]", f"{n:,}")
        macro(
            "MDD" + k,
            plan["mdd_current_design"],
            "a_pairs.planning_gap_3pp.mdd_current_design",
            f"{plan['mdd_current_design'] * 100:.2f}",
        )
    rounded = [
        round(numbers["ItemsLlama"]["value"] / 100) * 100,
        round(numbers["ItemsQwen"]["value"] / 100) * 100,
    ]
    macro(
        "ItemRangeRounded",
        rounded,
        "rounded to hundreds from ItemsLlama/ItemsQwen",
        f"{rounded[0]:,}--{rounded[1]:,}",
    )
    macro(
        "TargetGap",
        llama["planning_gap_3pp"]["target_gap"] * 100,
        "a_pairs.planning_gap_3pp.target_gap",
        "3",
    )
    for key, field in [
        ("FollowupGross", "total_followup_metered_usage_usd"),
        ("FollowupEstimate", "total_followup_estimate_usd"),
        ("ProjectEstimate", "project_estimate_usd"),
        ("FollowupForecast", "original_followup_forecast_usd"),
    ]:
        value = d["l_receipt"][field]
        macro(key, value, "l_receipt." + field, f"{value:.4f}")
    macro("TruncationsAten", d["a_summary"]["truncated"], "a_summary.truncated")
    macro("TruncationsLfour", d["l_summary"]["truncations"], "l_summary.truncations")
    macro("SyntaxFailuresAten", d["a_summary"]["syntax_failures"], "a_summary.syntax_failures")
    models = d["a_summary"]["models"]
    zero = d["a_greedy"]["batch_invariant"][models[0]]["changed_text_ci95"][1]
    macro(
        "ZeroUpper", zero, "a_greedy.batch_invariant.changed_text_ci95[1]", f"{zero * 100:.2f}\\%"
    )
    out.joinpath("numbers.tex").write_text(
        "% Generated from saved artifacts by scripts/paper_assets.py.\n"
        + "\n".join("\\newcommand{\\" + k + "}{" + v["tex"] + "}" for k, v in numbers.items())
        + "\n"
    )

    rows = []
    winner_cells = []
    for gpu, prefix in [("A10", "a"), ("L4", "l")]:
        for arm in ARMS:
            cells = []
            counts = []
            for run in BATCHES:
                a, b = [
                    round(d[prefix + "_greedy"][arm][name]["scores"][run] * 500)
                    for name in (target["a"], target["b"])
                ]
                winner = "Llama" if a > b else "Qwen" if b > a else "Tie"
                cells.append(winner)
                counts.append([a, b])
            rows.append([gpu, "Default" if arm == "default" else "Invariant", *cells])
            winner_cells.append(
                {"gpu": gpu, "arm": arm, "llama_qwen_counts": counts, "winners": cells}
            )
    tabular(
        out / "tables/winners.tex", "llccc", ["GPU", "Arm", "Batch 1", "Batch 8", "Batch 32"], rows
    )
    rows = []
    for gpu, prefix in [("A10", "a"), ("L4", "l")]:
        for name in d[prefix + "_summary"]["models"]:
            a, b = [d[prefix + "_greedy"][arm][name] for arm in ARMS]
            lo, hi = a["changed_text_ci95"]
            rows.append(
                [
                    gpu,
                    label(name),
                    f"{a['changed_text']} ({100 * a['changed_text_fraction']:.1f}\\%)",
                    a["changed_correctness"],
                    b["changed_text"],
                    b["changed_correctness"],
                    f"[{lo * 100:.2f}, {hi * 100:.2f}]",
                ]
            )
    tabular(
        out / "tables/changes.tex",
        "llrrrrc",
        ["GPU", "Model", "D text", "D correct", "I text", "I correct", "Expl. 95\\% D text CI"],
        rows,
    )
    rows = []
    for name, p in [("Llama / Qwen3-4B", llama), ("Qwen2.5-3B / Qwen3-1.7B", qwen)]:
        plan = p["planning_gap_3pp"]
        n = next(
            r["items_for_target_gap"] for r in plan["grid"] if r["samples_per_item_per_model"] == 10
        )
        rows.append([name, f"{plan['mdd_current_design'] * 100:.2f}", f"{n:,}"])
    tabular(out / "tables/mdd.tex", "lrr", ["Pair", "MDD (pp)", "Items needed"], rows)
    rows = []
    for pair in d["pairs"]:
        pname = (
            "Llama / Qwen3-4B" if pair["a"].startswith("meta-llama/") else "Qwen2.5-3B / Qwen3-1.7B"
        )
        for gpu in ("a10", "l4"):
            v = pair[gpu]["default"]
            lo, hi = v["ci95"]
            rows.append(
                [
                    pname,
                    gpu.upper(),
                    f"{v['estimate'] * 100:.2f}",
                    f"[{lo * 100:.2f}, {hi * 100:.2f}]",
                ]
            )
    tabular(out / "tables/flips.tex", "llrr", ["Pair", "GPU", "Flip (\\%)", "Expl. 95\\% CI"], rows)
    rows = []
    for pair in d["pairs"]:
        for gpu in ("a10", "l4"):
            for arm in ARMS:
                v = pair[gpu][arm]
                for index, run in enumerate(BATCHES):
                    lo, hi = v["difference_ci95"][index]
                    rows.append(
                        [
                            label(pair["a"]) + " minus " + label(pair["b"]),
                            gpu.upper(),
                            esc(arm),
                            [1, 8, 32][index],
                            f"{v['observed_differences'][index] * 100:+.2f}",
                            f"[{lo * 100:.2f}, {hi * 100:.2f}]",
                        ]
                    )
    tabular(
        out / "tables/gaps.tex",
        "lllrrr",
        ["Pair", "GPU", "Arm", "Batch", "Gap (pp)", "Expl. 95\\% CI (pp)"],
        rows,
    )
    rows = []
    for name in models:
        values = [
            d["sampling"]["metrics"][f"pass@{k}"]["items"]["models"][name] for k in (1, 5, 10)
        ]
        lo, hi = values[0]["ci"]
        rows.append(
            [
                label(name),
                f"{values[0]['estimate'] * 100:.2f}",
                f"[{lo * 100:.2f}, {hi * 100:.2f}]",
                f"{values[1]['estimate'] * 100:.2f}",
                f"{values[2]['estimate'] * 100:.2f}",
            ]
        )
    tabular(
        out / "tables/sampling.tex",
        "lrrrr",
        ["Model", "pass@1 (\\%)", "Expl. 95\\% CI", "pass@5", "pass@10"],
        rows,
    )
    seed_rows = []
    for pair in d["pairs"]:
        for gpu in ("a10", "l4"):
            for arm in ARMS:
                seed_rows.append(
                    [
                        label(pair["a"]) + " / " + label(pair["b"]),
                        gpu.upper(),
                        esc(arm),
                        pair[gpu][arm]["seed"],
                    ]
                )
    tabular(
        out / "tables/analysis-seeds.tex",
        "lllr",
        ["Pair", "GPU", "Arm", "Flip-analysis seed"],
        seed_rows,
    )
    rows = []
    settings = []
    for gpu, prefix, session in [("A10", "a", A10), ("L4", "l", L4)]:
        for name in d[prefix + "_summary"]["models"]:
            job_path = session / (name.rsplit("/", 1)[-1] + ".json")
            d["files"][str(job_path)] = job_path
            job = read(root / job_path)
            m = job["arms"][0]["metadata"]
            settings.append(
                {
                    "gpu": gpu,
                    "model": name,
                    "gpu_uuid": job["gpu_uuid"],
                    "driver": m["driver"],
                    "cuda": m["cuda"],
                    "python": m["python"],
                    "engine": m["engine"],
                    "host_cpu_count": job.get("host_cpu_count"),
                    "host_load_average": job.get("host_load_average"),
                    "packages": {
                        k: m["packages"][k] for k in ("vllm", "torch", "transformers", "tokenizers")
                    },
                    "worker_hashes": [
                        a["metadata"].get("worker_source_sha256") for a in job["arms"]
                    ],
                }
            )
            rows.append(
                [
                    gpu,
                    label(name),
                    m["driver"],
                    f"\\texttt{{{job['gpu_uuid'].replace('GPU-', '')[:8]}}}",
                    job.get("host_cpu_count", "not recorded"),
                ]
            )
    tabular(
        out / "tables/hardware.tex",
        "llllr",
        ["GPU", "Model", "Driver", "UUID prefix", "Visible host CPUs"],
        rows,
    )
    table = []
    for model in d["roster"]:
        table.append(
            [
                label(model["id"]),
                model["seed_model_index"],
                r"\texttt{" + model["revision"] + "}",
                esc(model["license"]),
            ]
        )
    tabular(
        out / "tables/revisions.tex",
        "lrlp{2.1cm}",
        ["Model", "Seed index", "Immutable revision", "License"],
        table,
    )
    counts = Counter("_".join(n.split("_")[:-1]) for n in d["subset"]["full_ids"])
    manifest = {
        "sources_sha256": {str(p): sha(root / p) for p in d["files"].values()},
        "macros": numbers,
        "winner_cells": winner_cells,
        "settings": settings,
        "category_counts": dict(counts),
        "new_inference_or_bootstrap": False,
        "generator_sha256": sha(Path(__file__)),
    }
    plot(d, out)
    generated = [
        out / "numbers.tex",
        *sorted((out / "tables").glob("*.tex")),
        *sorted((out / "figures").glob("*.pdf")),
    ]
    manifest["generated_sha256"] = {str(p.relative_to(root)): sha(p) for p in generated}
    (out / "artifact-map.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("Paper numbers, tables and vector figures rendered from saved artifacts only.")


def plot(d, out):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.size": 9,
            "pdf.fonttype": 42,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )
    pair = next(p for p in d["pairs"] if p["a"].startswith("meta-llama/"))
    fig, axes = plt.subplots(2, 2, figsize=(6.8, 3.4), sharey=True, layout="constrained")
    for row, (gpu, prefix) in enumerate([("A10", "a"), ("L4", "l")]):
        for col, arm in enumerate(ARMS):
            ax = axes[row, col]
            for n, marker, style in [(pair["a"], "o", "-"), (pair["b"], "s", "--")]:
                counts = [round(d[prefix + "_greedy"][arm][n]["scores"][r] * 500) for r in BATCHES]
                ax.plot(
                    [0, 1, 2],
                    counts,
                    color="0.1" if marker == "o" else "0.45",
                    marker=marker,
                    ls=style,
                    ms=4,
                    label=label(n),
                )
            ax.set_title(gpu + ": " + ("default" if arm == "default" else "invariant"))
            ax.set_xticks([0, 1, 2], [1, 8, 32])
            ax.grid(axis="y", alpha=0.2)
            if row == 1:
                ax.set_xlabel("Request batch size")
            if col == 0:
                ax.set_ylabel("Correct / 500")
            ax.set_ylim(455.5, 459.5)
            ax.set_yticks([456, 457, 458, 459])
    fig.legend(
        *axes[0, 0].get_legend_handles_labels(), loc="outside lower center", ncol=2, frameon=False
    )
    fig.savefig(out / "figures/rank-order.pdf")
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(6.8, 2.75), layout="constrained")
    names = d["a_summary"]["models"]
    offsets = {"serial": -0.22, "batch8": 0, "batch32": 0.22}
    markers = {"serial": "o", "batch8": "s", "batch32": "^"}
    for run in BATCHES:
        for i, name in enumerate(names):
            v = next(r for r in d["timing"] if r["model"] == name and r["configuration"] == run)
            mid = v["token_rate_ratio_median"]
            lo, hi = v["token_rate_ratio_range"]
            ax.errorbar(
                i + offsets[run],
                mid,
                yerr=[[mid - lo], [hi - mid]],
                fmt=markers[run],
                color="0.15",
                mfc="white" if run == "batch8" else "0.15",
                ms=4,
                capsize=2,
                label=("Batch " + {"serial": "1", "batch8": "8", "batch32": "32"}[run])
                if i == 0
                else None,
            )
    ax.axhline(1, color="0.55", ls=":", lw=1)
    ax.set_ylim(0.32, 1.03)
    ax.set_ylabel("Invariant / default tokens per second")
    ax.set_xticks(range(len(names)), [label(n).replace("Qwen", "Q") for n in names])
    ax.tick_params(axis="x", labelsize=8)
    ax.grid(axis="y", alpha=0.2)
    ax.legend(ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.18), frameon=False)
    fig.savefig(out / "figures/throughput.pdf")
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()
    build(args.root)
