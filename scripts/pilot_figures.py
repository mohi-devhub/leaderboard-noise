"""Generate GPU-scoped greedy intervention figures from a completed pilot."""

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("session", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = json.loads((args.session / "job-result.json").read_text())
    if result["status"] != "complete":
        raise ValueError("figures require a complete pilot")
    summary = json.loads((args.session / "greedy-summary.json").read_text())
    config = json.loads((args.session / "config.json").read_text())
    models = config["models"]
    colors = ["#345c83", "#a56b3b"]
    args.out.mkdir(parents=True, exist_ok=True)
    plotted = {"gpu": result["gpu"], "models": models, "changes": {}, "throughput_ratios": []}
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    for index, model in enumerate(models):
        for arm_index, arm in enumerate(config["arms"]):
            fraction = summary["arms"][arm]["models"][model]["changed_fraction"]
            plotted["changes"][model + ":" + arm] = fraction
            bars = axes[0].bar(
                index + (arm_index - 0.5) * 0.34,
                fraction * 100,
                width=0.32,
                color=colors[index],
                alpha=1 if arm_index == 0 else 0.4,
                label=arm if index == 0 else None,
            )
            axes[0].bar_label(bars, labels=[f"{fraction * 100:.0f}%"], padding=3, fontsize=8)
    axes[0].set(
        xticks=range(len(models)),
        xticklabels=[m.split("/")[-1] for m in models],
        ylabel="Items with changed decoded text (%)",
        ylim=(0, 100),
        title=f"Across batch sizes 1, 8, 32; N={config['items']}",
    )
    axes[0].legend(frameon=False)
    timings = {
        (arm["metadata"]["model"]["id"], arm["metadata"]["arm"], t["run_id"]): t
        for arm in result["arms"]
        for t in arm["metadata"]["timings"]
    }
    labels, values, shades = [], [], []
    for index, model in enumerate(models):
        for repeat in config["greedy_repeats"]:
            run = repeat["run_id"]
            ratio = (
                timings[model, "batch_invariant", run]["generated_tokens_per_second"]
                / timings[model, "default", run]["generated_tokens_per_second"]
            )
            plotted["throughput_ratios"].append(
                {"model": model, "configuration": run, "fix_over_default": ratio}
            )
            labels.append(model.split("/")[-1] + " / " + run)
            values.append(ratio)
            shades.append(colors[index])
    axes[1].barh(labels, values, color=shades)
    axes[1].axvline(1, color="black", linewidth=1, linestyle="--")
    axes[1].set(
        xlabel="Batch-invariant / default\noutput tokens per second",
        title="Single timing per configuration\nDescriptive throughput ratio",
    )
    axes[1].invert_yaxis()
    fig.suptitle(f"Pilot intervention on {result['gpu']} — hardware-specific observations")
    for ax in axes:
        ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    for suffix in ["png", "pdf"]:
        fig.savefig(args.out / ("greedy-intervention." + suffix), dpi=180)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for index, model in enumerate(models):
        for arm in config["arms"]:
            values = []
            for repeat in config["greedy_repeats"]:
                report = json.loads(
                    (args.session / f"analysis-{arm}-{repeat['run_id']}.json").read_text()
                )
                values.append(
                    report["metrics"]["pass@1"]["items"]["models"][model]["estimate"] * 100
                )
            ax.plot(
                [r["request_batch_size"] for r in config["greedy_repeats"]],
                values,
                marker="o",
                linestyle="-" if arm == "default" else "--",
                color=colors[index],
                label=model.split("/")[-1] + " / " + arm,
            )
    ax.set(
        xticks=[1, 8, 32],
        xlabel="Request batch size",
        ylabel="Greedy pass@1 (%)",
        ylim=(0, 100),
        title=f"Observed scores on {result['gpu']}; N={config['items']}",
    )
    ax.legend(frameon=False, fontsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    for suffix in ["png", "pdf"]:
        fig.savefig(args.out / ("greedy-scores." + suffix), dpi=180)
    plt.close(fig)
    plotted["job_result_sha256"] = hashlib.sha256(
        (args.session / "job-result.json").read_bytes()
    ).hexdigest()
    (args.out / "plot-data.json").write_text(json.dumps(plotted, indent=2) + "\n")


if __name__ == "__main__":
    main()
