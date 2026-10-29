"""Plot the observed rank order on each GPU from saved, scored summaries."""

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
    approval = json.loads((args.session / "approval.json").read_text())
    sources = {
        "comparison": args.session / "pairwise-gpu-comparison.json",
        "L4": args.session / "greedy-summary.json",
        "A10": Path(approval["a10_session"]) / "greedy-summary.json",
    }
    if not sources["comparison"].exists():
        print("No complete pair available; no result figure generated.")
        return
    pairs = json.loads(sources["comparison"].read_text())
    data = {device: json.loads(sources[device].read_text()) for device in ("A10", "L4")}
    args.out.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    for index, pair in enumerate(pairs, 1):
        fig, axes = plt.subplots(2, 2, figsize=(11, 7), sharey=True, layout="constrained")
        points = []
        for row, device in enumerate(("A10", "L4")):
            for column, arm in enumerate(("default", "batch_invariant")):
                ax = axes[row, column]
                for model_index, name in enumerate((pair["a"], pair["b"])):
                    scores = data[device][arm][name]["scores"]
                    counts = [round(scores[k] * 500) for k in ("serial", "batch8", "batch32")]
                    points.extend(counts)
                    ax.plot(
                        range(3),
                        counts,
                        marker="o" if model_index == 0 else "s",
                        linestyle="-" if model_index == 0 else "--",
                        color=("#355f84", "#b06d35")[model_index],
                        label=name.rsplit("/", 1)[-1],
                    )
                ax.set_xticks(range(3), [1, 8, 32])
                ax.set_title(f"{device}: {arm}")
                ax.grid(alpha=0.2)
                if row == 1:
                    ax.set_xlabel("Request batch size")
                if column == 0:
                    ax.set_ylabel("Correct calls out of the same 500 items")
        axes[0, 0].set_ylim(min(points) - 0.5, max(points) + 0.5)
        if max(points) - min(points) <= 12:
            axes[0, 0].set_yticks(range(min(points), max(points) + 1))
        handles, labels = axes[0, 0].get_legend_handles_labels()
        fig.legend(handles, labels, loc="outside lower center", ncols=2)
        old_flip = pair["a10"]["default"]["observed_strict_flip"]
        new_flip = pair["l4"]["default"]["observed_strict_flip"]
        fig.suptitle(
            f"Greedy rank order across A10 and L4\nDefault strict flips: A10={old_flip}, L4={new_flip}; zoomed y-axis, one call = 0.2 points"
        )
        for suffix in ("png", "pdf"):
            fig.savefig(args.out / f"rank-order-pair{index}.{suffix}", dpi=180, bbox_inches="tight")
        plt.close(fig)
    (args.out / "plot-data.json").write_text(
        json.dumps(
            {
                "sources_sha256": {
                    str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                    for path in sources.values()
                },
                "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
