"""Render only supplied analysis, never synthesized model results."""

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main():
    p = argparse.ArgumentParser()
    p.add_argument("report", type=Path)
    p.add_argument("--out", type=Path, default=Path("figures"))
    args = p.parse_args()
    report = json.loads(args.report.read_text())
    args.out.mkdir(parents=True, exist_ok=True)
    for metric, modes in report["metrics"].items():
        for mode, data in modes.items():
            diagnostic = mode == "sampling" and metric != "pass@1"
            rows = data["models"]
            names = list(rows)
            fig, ax = plt.subplots(figsize=(8, max(3, len(names) * 0.5)))
            # Plot endpoints directly: percentile intervals need not enclose the point estimate.
            for y, name in enumerate(names):
                r = rows[name]
                ax.plot(r["ci"], [y, y], color="#345c83", linewidth=2)
                ax.plot(r["estimate"], y, "o", color="#172c40")
            ax.set(
                yticks=range(len(names)),
                yticklabels=names,
                xlim=(0, 1),
                xlabel=(
                    f"{metric} (fraction), empirical resampling range"
                    if diagnostic
                    else f"{metric} (fraction), {report['config']['confidence']:.0%} percentile CI"
                ),
                title=f"{mode} {'diagnostic' if diagnostic else 'uncertainty'}; N={report['n_items']}",
            )
            ax.invert_yaxis()
            ax.spines[["top", "right"]].set_visible(False)
            fig.tight_layout()
            fig.savefig(args.out / f"{metric.replace('@', '-')}-{mode}.png", dpi=180)
            fig.savefig(args.out / f"{metric.replace('@', '-')}-{mode}.pdf")
            plt.close(fig)
            if data["pairwise"]:
                fig, ax = plt.subplots(figsize=(8, max(3, len(data["pairwise"]) * 0.4)))
                pairs = data["pairwise"]
                ax.barh(range(len(pairs)), [r["p_a_beats_b"] for r in pairs], color="#345c83")
                ax.set(
                    yticks=range(len(pairs)),
                    yticklabels=[r["a"] + " > " + r["b"] for r in pairs],
                    xlim=(0, 1),
                    xlabel="Bootstrap win fraction (strict wins; ties separate)",
                    title=f"{metric}: {mode} resampling stability",
                )
                fig.tight_layout()
                fig.savefig(args.out / f"{metric.replace('@', '-')}-{mode}-wins.png", dpi=180)
                plt.close(fig)


if __name__ == "__main__":
    main()
