"""Render study figures exclusively from recorded analysis summaries."""

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def main():
    p = argparse.ArgumentParser()
    p.add_argument("session", type=Path)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    files = [
        "summary.json",
        "greedy-summary.json",
        "pairwise-flips.json",
        "throughput-summary.json",
    ]
    data = {name: json.loads((args.session / name).read_text()) for name in files}
    names = data["summary.json"]["models"]
    labels = [name.rsplit("/", 1)[-1] for name in names]
    gpu = data["summary.json"]["gpu"]
    colors = ["#355f84", "#a56d3a"]
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})

    def export(fig, name):
        for suffix in ("png", "pdf"):
            fig.savefig(args.out / f"{name}.{suffix}", dpi=180, bbox_inches="tight")
        plt.close(fig)

    fig, ax = plt.subplots(figsize=(11, 6), layout="constrained")
    ys = np.arange(len(names))
    for index, arm in enumerate(("default", "batch_invariant")):
        records = [data["greedy-summary.json"][arm][name] for name in names]
        values = np.array([r["changed_text_fraction"] for r in records]) * 100
        intervals = np.array([r["changed_text_ci95"] for r in records]) * 100
        y = ys + (index - 0.5) * 0.3
        ax.barh(y, values, height=0.28, color=colors[index], label=arm)
        ax.errorbar(
            values,
            y,
            xerr=[np.maximum(0, values - intervals[:, 0]), np.maximum(0, intervals[:, 1] - values)],
            fmt="none",
            ecolor=colors[index],
            capsize=3,
        )
        for value, yy, r in zip(values, y, records, strict=True):
            ax.annotate(
                f"{r['changed_text']}/500",
                (max(value, r["changed_text_ci95"][1] * 100), yy),
                xytext=(5, 0),
                textcoords="offset points",
                va="center",
                fontsize=8,
            )
    ax.set_yticks(ys, labels)
    ax.invert_yaxis()
    ax.set_xlabel("Items with different exact text across batch sizes 1, 8, and 32 (%)")
    ax.set_xlim(left=0)
    ax.margins(x=0.16)
    ax.legend()
    ax.set_title(
        f"Greedy text sensitivity on {gpu}\nWilson 95% intervals; independent-item approximation"
    )
    export(fig, "greedy-text-changes")

    selected = [
        r
        for r in data["pairwise-flips.json"]
        if r["observed_close"] or r["preselected_from_published_scores"]
    ]
    if selected:
        fig, ax = plt.subplots(figsize=(12, max(4, len(selected) * 0.8)), layout="constrained")
        labels_pair = [
            r["a"].rsplit("/", 1)[-1] + "\nvs " + r["b"].rsplit("/", 1)[-1] for r in selected
        ]
        for index, arm in enumerate(("default", "batch_invariant")):
            for j, pair in enumerate(selected):
                r = pair["arms"][arm]
                yy = j + (index - 0.5) * 0.3
                lo, hi = np.array(r["ci95"]) * 100
                ax.plot([lo, hi], [yy, yy], color=colors[index], linewidth=2)
                ax.scatter(
                    r["estimate"] * 100,
                    yy,
                    color=colors[index],
                    s=30,
                    label=arm if j == 0 else None,
                    zorder=3,
                )
                if r["collapsed_outer_interval"]:
                    ax.annotate(
                        "collapsed",
                        (hi, yy),
                        xytext=(5, 0),
                        textcoords="offset points",
                        va="center",
                        fontsize=7,
                    )
        ax.set_yticks(np.arange(len(selected)), labels_pair)
        ax.invert_yaxis()
        ax.set_xlabel(
            "Paired item-resample fraction with opposite strict orders across batch settings (%)"
        )
        ax.set_xlim(-1, 101)
        ax.legend()
        ax.set_title(
            f"Batch-induced rank flips on {gpu}\nExploratory outer-bootstrap intervals; boundary collapse is not certainty"
        )
        export(fig, "close-pair-flips")

    records = data["throughput-summary.json"]
    fig, ax = plt.subplots(figsize=(11, 10), layout="constrained")
    for index, r in enumerate(records):
        values = r["token_rate_ratios"]
        ax.plot([min(values), max(values)], [index, index], color="#6e8498", linewidth=2)
        ax.scatter(values, np.repeat(index, 3) + [-0.1, 0, 0.1], color=colors[0], s=18, alpha=0.65)
        ax.scatter(
            r["token_rate_ratio_median"], index, color=colors[1], marker="|", s=140, zorder=4
        )
    ax.axvline(1, linestyle="--", color="black", linewidth=1)
    ax.set_yticks(
        range(len(records)),
        [r["model"].rsplit("/", 1)[-1] + " / " + r["configuration"] for r in records],
    )
    ax.invert_yaxis()
    ax.set_xlabel("Batch-invariant / default generated-token rate (three matched repetitions)")
    ax.set_title(
        f"Observed configuration overhead on {gpu}\nDots show repetitions; orange marks show medians; lines show ranges"
    )
    export(fig, "throughput-ranges")

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.8), sharey=True, layout="constrained")
    palette = plt.get_cmap("tab10")
    for index, arm in enumerate(("default", "batch_invariant")):
        ax = axes[index]
        for j, name in enumerate(names):
            scores = data["greedy-summary.json"][arm][name]["scores"]
            ax.plot(
                [0, 1, 2],
                [scores[k] * 100 for k in ("serial", "batch8", "batch32")],
                marker="o",
                color=palette(j),
                label=labels[j],
            )
        ax.set_xticks([0, 1, 2], [1, 8, 32])
        ax.set_xlabel("Request batch size")
        ax.set_title(arm)
        ax.grid(alpha=0.2)
    axes[0].set_ylabel("Greedy pass@1 on 500 items (%)")
    axes[1].legend(fontsize=8, loc="upper left", bbox_to_anchor=(1.01, 1))
    fig.suptitle(f"Observed score order across batch configurations on {gpu}")
    export(fig, "greedy-score-order")

    observed_flips = [
        pair
        for pair in data["pairwise-flips.json"]
        if pair["arms"]["default"]["observed_strict_flip"]
    ]
    for index, pair in enumerate(observed_flips, 1):
        fig, axes = plt.subplots(1, 2, figsize=(10, 4.5), sharey=True, layout="constrained")
        points = []
        for ax, arm in zip(axes, ("default", "batch_invariant"), strict=True):
            for model_index, name in enumerate((pair["a"], pair["b"])):
                scores = data["greedy-summary.json"][arm][name]["scores"]
                counts = [round(scores[k] * 500) for k in ("serial", "batch8", "batch32")]
                points.extend(counts)
                ax.plot(
                    range(3),
                    counts,
                    marker="o" if model_index == 0 else "s",
                    linestyle="-" if model_index == 0 else "--",
                    color=palette(model_index),
                    label=name.rsplit("/", 1)[-1],
                    markersize=6,
                )
            ax.set_xticks(range(3), [1, 8, 32])
            ax.set_xlabel("Request batch size")
            ax.set_title(arm)
            ax.grid(alpha=0.2)
        axes[0].set_ylabel("Correct calls out of the same 500 items")
        axes[0].set_yticks(range(min(points), max(points) + 1))
        axes[0].set_ylim(min(points) - 0.5, max(points) + 0.5)
        handles, labels_flip = axes[0].get_legend_handles_labels()
        fig.legend(handles, labels_flip, loc="outside lower center", ncols=2, fontsize=8)
        fig.suptitle(
            f"Observed strict ranking flip on {gpu}\nZoomed y-axis; one call is 0.2 points"
        )
        export(fig, f"observed-rank-flip-{index}")
    manifest = {
        "session": str(args.session),
        "gpu": gpu,
        "sources_sha256": {
            name: hashlib.sha256((args.session / name).read_bytes()).hexdigest() for name in files
        },
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    (args.out / "plot-data.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
