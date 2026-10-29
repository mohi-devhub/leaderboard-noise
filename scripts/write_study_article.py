"""Render the combined article and report from saved summaries; no network or inference."""

import argparse
import hashlib
import json
import os
from pathlib import Path


A10 = Path("results/study-20261028T065939Z")
L4 = Path("results/l4-continuation-20261028T224638Z")
BATCHES = ((1, "serial"), (8, "batch8"), (32, "batch32"))
ARMS = ("default", "batch_invariant")
LEAD = "Batch size changed about 2–5% of greedy answers. For the near-tied Llama3B/Qwen3-4B pair, the observed flip was a one-item margin out of 500, within exploratory paired 95% intervals of roughly ±3 percentage points. The separate sampling analysis projects roughly 800–1,100 items to resolve a 3-point gap, with ten sampled answers per item per model."
MITIGATION = "Under batch invariance, decoded outputs were identical across A10 and L4 for all four replicated models. Switching to invariance can itself change the winner: at A10 batch 1, the lead moves from Qwen3-4B to Llama3B. Median token throughput was 32–60% lower in the repeated A10 timing study."


def read(path):
    return json.loads(path.read_text())


def short(name):
    return name.rsplit("/", 1)[-1]


def pct(value):
    return f"{value:.2%}"


def ci(values):
    return f"[{pct(values[0])}, {pct(values[1])}]"


def rate(value):
    return f"{pct(value['estimate'])} {ci(value['ci95'])}"


def table(headers, rows):
    return "\n".join(
        ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
        + ["| " + " | ".join(map(str, row)) + " |" for row in rows]
    )


def link(path, output):
    return Path(os.path.relpath(path, output.parent)).as_posix()


def load_study(a10, l4):
    paths = {
        "a10_summary": a10 / "summary.json",
        "a10_receipt": a10 / "receipt.json",
        "sampling": a10 / "analysis-sampling.json",
        "a10_greedy": a10 / "greedy-summary.json",
        "a10_pairs": a10 / "pairwise-flips.json",
        "timing": a10 / "throughput-summary.json",
        "l4_summary": l4 / "summary.json",
        "l4_receipt": l4 / "receipt.json",
        "l4_greedy": l4 / "greedy-summary.json",
        "pairs": l4 / "pairwise-gpu-comparison.json",
        "agreement": l4 / "cross-gpu-agreement.json",
    }
    data = {name: read(path) for name, path in paths.items()}
    if (
        data["a10_summary"]["total_predictions"] != 58800
        or data["sampling"]["n_items"] != 500
        or data["l4_summary"]["status"] != "complete"
        or data["l4_summary"]["predictions"] != 12000
        or len(data["pairs"]) != 2
    ):
        raise ValueError("both saved study cohorts must be complete")
    for receipt in (data["a10_receipt"], data["l4_receipt"]):
        if (
            not receipt["own_apps_stopped"]
            or receipt["own_running_containers"]
            or receipt["active_reservations_usd"]
        ):
            raise ValueError("confirmed shutdown and released holds are required")
    if (
        data["l4_receipt"]["total_followup_estimate_usd"] > 5
        or data["l4_receipt"]["project_estimate_usd"] > 12
    ):
        raise ValueError("recorded spend exceeds a cap")
    data["sources"] = paths
    data["a10_path"], data["l4_path"] = a10, l4
    return data


def count(data, gpu, arm, name, run):
    return round(data[gpu.lower() + "_greedy"][arm][name]["scores"][run] * 500)


def winner_rows(data):
    rows = []
    for pair in data["pairs"]:
        a, b = pair["a"], pair["b"]
        for gpu in ("A10", "L4"):
            for batch, run in BATCHES:
                ca, cb = (count(data, gpu, "default", n, run) for n in (a, b))
                winner = short(a) if ca > cb else short(b) if cb > ca else "Tie"
                rows.append(
                    {
                        "pair": f"{short(a)} vs {short(b)}",
                        "gpu": gpu,
                        "batch": batch,
                        "a": a,
                        "b": b,
                        "a_correct": ca,
                        "b_correct": cb,
                        "higher_rank": winner,
                    }
                )
    return rows


def winners(data):
    return table(
        [
            "Pair, A vs B",
            "GPU",
            "Default batch",
            "A correct / 500",
            "B correct / 500",
            "Higher rank",
        ],
        [
            [r[k] for k in ("pair", "gpu", "batch", "a_correct", "b_correct", "higher_rank")]
            for r in winner_rows(data)
        ],
    )


def invariant_scores(data):
    rows = []
    for pair in data["pairs"]:
        for gpu in ("A10", "L4"):
            counts = [
                [count(data, gpu, "batch_invariant", name, run) for _, run in BATCHES]
                for name in (pair["a"], pair["b"])
            ]
            ca, cb = (" / ".join(map(str, values)) for values in counts)
            winner = short(pair["a"] if counts[0][0] > counts[1][0] else pair["b"])
            rows.append([f"{short(pair['a'])} vs {short(pair['b'])}", gpu, ca, cb, winner])
    return table(
        [
            "Pair, A vs B",
            "GPU",
            "Invariant A, batches 1 / 8 / 32",
            "Invariant B, batches 1 / 8 / 32",
            "Higher at every batch",
        ],
        rows,
    )


def flip_rates(data):
    rows = []
    for pair in data["pairs"]:
        for gpu in ("A10", "L4"):
            for arm in ARMS:
                v = pair[gpu.lower()][arm]
                rows.append(
                    [
                        f"{short(pair['a'])} vs {short(pair['b'])}",
                        gpu,
                        arm,
                        "Yes" if v["observed_strict_flip"] else "No",
                        rate(v),
                    ]
                )
    return table(
        [
            "Pair",
            "GPU",
            "Arm",
            "Full-set strict flip",
            "Bootstrap flip fraction [exploratory 95% interval]",
        ],
        rows,
    )


def sampling(data):
    rows = []
    for name in data["a10_summary"]["models"]:
        values = [
            data["sampling"]["metrics"][f"pass@{k}"]["items"]["models"][name] for k in (1, 5, 10)
        ]
        rows.append(
            [
                short(name),
                pct(values[0]["estimate"]),
                ci(values[0]["ci"]),
                pct(values[1]["estimate"]),
                pct(values[2]["estimate"]),
            ]
        )
    return table(
        [
            "Model",
            "A10 pass@1",
            "Exploratory 95% item-bootstrap interval",
            "Unbiased pass@5",
            "Unbiased pass@10",
        ],
        rows,
    )


def changes(data):
    rows = []
    for gpu in ("A10", "L4"):
        values = data[gpu.lower() + "_greedy"]
        for name in data[gpu.lower() + "_summary"]["models"]:
            a, b = (values[arm][name] for arm in ARMS)
            cells = [
                f"{r['changed_text']}/500, {pct(r['changed_text_fraction'])} "
                f"{ci(r['changed_text_ci95'])}"
                for r in (a, b)
            ]
            rows.append(
                [
                    gpu,
                    short(name),
                    *cells,
                    f"{a['changed_correctness']} / {b['changed_correctness']}",
                ]
            )
    return table(
        [
            "GPU",
            "Model",
            "Default text changes [exploratory Wilson 95% interval]",
            "Invariant text changes [exploratory Wilson 95% interval]",
            "Correctness changes, default / invariant",
        ],
        rows,
    )


def throughput(data, compact=False):
    def cell(row, kind):
        lo, hi = row[kind + "_range"]
        return f"{row[kind + '_median']:.3f} [{lo:.3f}, {hi:.3f}]"

    if compact:
        lookup = {(r["model"], r["configuration"]): r for r in data["timing"]}
        return table(
            [
                "Model on A10",
                "Batch 1 ratio [observed range]",
                "Batch 8 ratio [observed range]",
                "Batch 32 ratio [observed range]",
            ],
            [
                [short(n)] + [cell(lookup[n, run], "token_rate_ratio") for _, run in BATCHES]
                for n in data["a10_summary"]["models"]
            ],
        )
    return table(
        [
            "Model on A10",
            "Batch",
            "Token-rate ratio, median [observed range]",
            "Completion-rate ratio, median [observed range]",
        ],
        [
            [
                short(r["model"]),
                r["configuration"],
                cell(r, "token_rate_ratio"),
                cell(r, "completion_rate_ratio"),
            ]
            for r in data["timing"]
        ],
    )


def planning(data, close_only=False):
    rows = []
    for pair in data["a10_pairs"]:
        if not (
            pair["observed_close"] or (pair["preselected_from_published_scores"] and not close_only)
        ):
            continue
        p = pair["planning_gap_3pp"]
        if p["status"] != "approximate_pilot_projection":
            rows.append([f"{short(pair['a'])} vs {short(pair['b'])}", p["status"], "undefined"])
            continue
        required = next(
            r["items_for_target_gap"] for r in p["grid"] if r["samples_per_item_per_model"] == 10
        )
        rows.append(
            [
                f"{short(pair['a'])} vs {short(pair['b'])}",
                f"{100 * p['mdd_current_design']:.2f}",
                required,
            ]
        )
    return table(
        ["Pair", "Approximate MDD, percentage points", "Items projected for a 3-point gap"], rows
    )


def costs(data):
    a, l4_receipt = data["a10_receipt"], data["l4_receipt"]
    return table(
        ["Scope", "Forecast USD", "Provisional gross metering USD", "Conservative estimate USD"],
        [
            [
                "A10 remaining-five job",
                f"{a['forecast_remaining_job_usd']:.4f}",
                f"{float(a['app_specific_gross_metered_remaining_usage_usd']):.4f}",
                f"{a['estimated_remaining_spend_usd']:.4f}",
            ],
            [
                "A10 six-model study",
                f"{a['forecast_full_study_usd']:.4f}",
                f"{float(a['app_specific_gross_metered_study_usage_usd']):.4f}",
                f"{float(a['estimated_study_spend_usd']):.4f}",
            ],
            [
                "L4 follow-up, both allocations",
                f"{l4_receipt['original_followup_forecast_usd']:.4f}",
                f"{l4_receipt['total_followup_metered_usage_usd']:.4f}",
                f"{l4_receipt['total_followup_estimate_usd']:.4f}",
            ],
            [
                "Whole project, including pilot and failed attempts",
                "Multiple approvals",
                "Early attempts not fully attributable",
                f"{l4_receipt['project_estimate_usd']:.4f} / 12",
            ],
        ],
    )


def all_a10_pairs(data):
    rows = []
    for pair in data["a10_pairs"]:
        label = (
            "published-score preselection"
            if pair["preselected_from_published_scores"]
            else ("observed close" if pair["observed_close"] else "other")
        )
        for arm in (*ARMS, "sampling"):
            v = pair["sampling"] if arm == "sampling" else pair["arms"][arm]
            rows.append(
                [
                    f"{short(pair['a'])} vs {short(pair['b'])}",
                    label,
                    "Yes" if pair["same_physical_gpu"] else "No",
                    arm,
                    "n/a" if arm == "sampling" else str(v["observed_strict_flip"]),
                    rate(v),
                ]
            )
    return table(
        [
            "A10 pair",
            "Selection",
            "Same physical GPU",
            "Condition",
            "Full-set batch flip",
            "Flip fraction [exploratory 95% interval]",
        ],
        rows,
    )


def differences(data):
    rows = []
    for pair in data["pairs"]:
        for gpu in ("A10", "L4"):
            for arm in ARMS:
                v = pair[gpu.lower()][arm]
                for i, (batch, _) in enumerate(BATCHES):
                    rows.append(
                        [
                            f"{short(pair['a'])} minus {short(pair['b'])}",
                            gpu,
                            arm,
                            batch,
                            f"{v['observed_differences'][i] * 100:+.2f}",
                            ci(v["difference_ci95"][i]),
                        ]
                    )
    return table(
        [
            "Pair difference",
            "GPU",
            "Arm",
            "Batch",
            "Gap, percentage points",
            "Exploratory 95% paired item-bootstrap interval",
        ],
        rows,
    )


def render(data, output, full=False):
    a10, l4 = data["a10_path"], data["l4_path"]

    def image(session, name):
        return link(Path("figures") / session.name / name, output)

    sections = []

    def add(title, body):
        sections.append(f"## {title}\n\n{body}")

    add(
        "Which model ranks higher at each default batch size?",
        "\n\n".join(
            [
                "Every count is correct calls out of the same 500 items. Higher rank means a higher observed score, not established population superiority. Batch size is controlled offline request submission, with the engine limit fixed at 64 sequences.",
                winners(data),
                "On A10, Qwen3-4B ranks above Llama3B at batch 1, they tie at batch 8, and Llama3B ranks above Qwen3-4B at batch 32. On L4, Llama3B ranks above Qwen3-4B at batch 1, they tie at batch 8, and Qwen3-4B ranks above Llama3B at batch 32. Thus the strict full-set flip reproduces, but the winner at each untied setting reverses between GPUs.",
                "Qwen3-1.7B ranks above Qwen2.5-3B at every default batch size on both GPUs. A near tie does not require a flip.",
                f"![Llama and Qwen default and invariant scores, zoomed y-axis]({image(l4, 'rank-order-pair1.png')})",
                f"![Qwen pair default and invariant scores, zoomed y-axis]({image(l4, 'rank-order-pair2.png')})",
                "Both figures zoom the vertical axis. One correct call equals 0.2 percentage points.",
            ]
        ),
    )
    add(
        "Batch invariance removes the observed batch dependence",
        "\n\n".join(
            [
                invariant_scores(data),
                "Under batch invariance, Llama3B ranks above Qwen3-4B at all three batch sizes on both GPUs. Qwen3-1.7B ranks above Qwen2.5-3B throughout. For all four replicated models, invariant text and correctness match exactly between the recorded A10 and L4 runs.",
                "Across all 15 A10 model pairs, default decoding produced one full-set batch flip and invariant decoding produced none. Across the two L4 comparison pairs, the corresponding counts were one and zero. Changing from default to invariant decoding can itself change a winner at a fixed batch size. Stability is not the same as improved accuracy.",
            ]
        ),
    )
    add(
        "Bootstrap flips and exploratory uncertainty",
        "\n\n".join(
            [
                "A full-set flip requires opposite strict orders at two batch settings on the actual 500 questions. Ties alone do not count. A bootstrap flip fraction asks how often that happens after resampling the questions together across models and batch settings.",
                flip_rates(data),
                "All confidence intervals in this article and the combined report are exploratory and unadjusted for multiple comparisons. Flip fractions use 5,000 paired item resamples. Their outer percentile intervals use 500 outer and 1,000 inner draws. The discontinuous ranking statistic and inner Monte Carlo variation limit interpretation. A collapsed [0, 0] interval does not establish that population flips are impossible. Paired score-difference intervals for the close pairs include zero.",
                f"The [saved paired comparisons]({link(l4 / 'pairwise-gpu-comparison.json', output)}) retain exploratory score-difference intervals at every batch and separate Monte Carlo precision intervals. A nonzero bootstrap flip fraction can coexist with no observed full-set flip, as the Qwen pair demonstrates.",
            ]
        ),
    )
    add(
        "The throughput cost was measured on A10",
        "\n\n".join(
            [
                "Invariant/default median token-rate ratios range from about 0.400 to 0.678 across 18 A10 configurations, or about 32–60% lower throughput. Each configuration has three matched repetitions on the same 100-item subset, alternating arm order. Table ranges are observed ranges across three trials, not confidence intervals.",
                throughput(data, compact=not full),
                "The timed region includes generation, synchronization, and output collection. Loading, smoke checks, and warmup are excluded from throughput and included in cost. Token counts and completion rates are both retained because output lengths can change. We scored all timing outputs to detect fast failures.",
                "These are configuration measurements without limiter profiling or production tuning. L4 has no repeated throughput study; its generation durations support cost accounting only. The 32–60% cost must not be read as an L4 measurement or a universal vLLM overhead.",
                f"![A10 throughput ratios and three-trial ranges]({image(a10, 'throughput-ranges.png')})",
            ]
        ),
    )
    add(
        "Sampling accuracy remains a separate A10 experiment",
        "\n\n".join(
            [
                "Each A10 model has ten sampled completions per item at temperature 0.7, using vLLM's n parameter. Exploratory pass@1 intervals resample whole items. Pass@5 and pass@10 use unbiased point estimators; their exploratory item intervals remain in the saved analysis. L4 adds no stochastic samples.",
                sampling(data),
                f"![A10 sampling accuracy with exploratory item-bootstrap intervals]({image(a10, 'pass-1-items.png')})",
                "The intervals in this sampling figure are exploratory 95% item-bootstrap intervals.",
            ]
        ),
    )
    add(
        "Text changes and correctness changes",
        "\n\n".join(
            [
                "An item changes text if any of its three batch outputs differ. Correctness changes count items whose official BFCL pass/fail result differs. Wilson intervals below are exploratory under an independent-item approximation. Questions recur across models and GPUs, so these observations must not be pooled as independent questions.",
                changes(data),
                "Zero invariant changes on 500 items gives a per-model exploratory Wilson upper bound of about 0.76%. Shared function templates can violate item independence. Stable scores can hide text changes, as Llama's A10 default counts show.",
            ]
        ),
    )
    add(
        "How much evaluation would a three-point gap need?",
        "\n\n".join(
            [
                "These exploratory planning projections use A10 stochastic pass@1 variance estimates, 500 items and ten samples per model, a two-sided 5% test, and 80% power. They are approximations, not guarantees of a significant result.",
                planning(data, close_only=not full),
                "For both close pairs, increasing samples alone at the existing 500 questions cannot reach a three-point target under the estimated variance components. More answers reduce sampling noise but do not remove differences between questions.",
            ]
        ),
    )
    if full:
        add(
            "All A10 pairs, including null and preselected comparisons",
            "\n\n".join(
                [
                    "The three published-score preselected pairs separated by 4.60, 11.40, and 16.00 points on default serial decoding. The two close pairs were selected exploratorily on A10, then preselected for L4. No model or question was replaced after results. Sampling fractions below mean reversal of the fixed observed stochastic order; they are distinct from batch flips.",
                    all_a10_pairs(data),
                    f"The [full A10 pair data]({link(a10 / 'pairwise-flips.json', output)}) also retain exploratory Monte Carlo precision and paired difference intervals. Generic CLI win fractions are empirical bootstrap fractions, not posterior probabilities.",
                ]
            ),
        )
        add("Exploratory paired gap intervals for the replicated pairs", differences(data))
        rows = []
        for gpu in ("A10", "L4"):
            s = data[gpu.lower() + "_summary"]
            for name in s["models"]:
                rows.append([gpu, short(name), s["gpu_uuid_by_model"][name]])
        add("Physical GPU assignment", table(["Tier", "Model", "Recorded GPU UUID"], rows))
    add(
        "Cost, interruption recovery, and cleanup",
        "\n\n".join(
            [
                costs(data),
                "Cost rows overlap: the remaining-five job is part of the A10 study, and both studies are part of the project. Settled invoice actuals are unknown. Gross metering is provisional, attributed by exact app ID, and excludes credit offsets and unrelated qunti-check usage.",
                "The first L4 allocation was preempted after the Llama/Qwen pair completed. Its checkpoints and all 6,000 scored rows were preserved byte for byte. Only the unfinished Qwen pair resumed, on another L4. Failed partial work is charged but not scored or imputed. Post-preemption GPU queue waiting is excluded from resource time. A persistent execution claim prevents platform replay from regenerating outputs, and saved call IDs permit reconnection without job resubmission.",
                "Every requested comparison pair shares a physical GPU within its tier, and each model's arms stay on that card. The A10 anchor used an earlier A10. The two L4 pairs use separate cards after recovery. The complete article/report cohort has 70,800 scored outputs: 58,800 on A10, including 10,800 timing outputs, plus 12,000 greedy L4 outputs. The same 500 items recur throughout. There are 17 A10 length truncations and 913 A10 AST syntax/format failures, and no L4 length truncations. Incorrect outputs remain in the denominator.",
                "All owned study apps are stopped, running owned containers are zero, holds are released, and temporary results volumes were deleted after hash verification. qunti-check was untouched. This editorial merge uses saved artifacts only and launches no compute.",
                f"[A10 receipt]({link(a10 / 'receipt.json', output)}), [combined L4/project receipt]({link(l4 / 'receipt.json', output)}), [budget]({link(Path('BUDGET.md'), output)}), and [decisions]({link(Path('DECISIONS.md'), output)}) preserve the accounting and operational evidence.",
            ]
        ),
    )
    return "\n\n".join(sections)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("session", type=Path, nargs="?", default=A10)
    parser.add_argument("--l4-session", type=Path, default=L4)
    parser.add_argument("--out", type=Path, default=Path("blog/STUDY.md"))
    parser.add_argument("--report", type=Path, default=Path("results/REPORT.md"))
    parser.add_argument("--manifest", type=Path, default=Path("results/combined-sources.json"))
    args = parser.parse_args()
    data = load_study(args.session, args.l4_session)
    text = args.out.read_text()
    start, rest = text.split("<!-- results:start -->", 1)
    _, end = rest.split("<!-- results:end -->", 1)
    article = (
        start + "<!-- results:start -->\n" + render(data, args.out) + "\n<!-- results:end -->" + end
    )
    report = (
        "# Batching changes 2–5% of greedy answers: combined A10/L4 report\n\n"
        + LEAD
        + "\n\n"
        + MITIGATION
        + "\n\nCompleted October 29, 2026. All confidence intervals are exploratory. "
        "This report combines saved six-model A10 results and the four-model L4 replication. "
        "It does not pool repeated questions or add model runs.\n\n"
        + render(data, args.report, full=True)
        + "\n\n## Methods and interpretation\n\n"
        + f"The [merged article]({link(args.out, args.report)}) explains selection, prompting, seeds, "
        "mitigation, and inference controls. GPU family is not causally isolated: generation history, "
        "CPU caps, host, and driver also differ. Each comparison has only one recorded card per GPU family. "
        "The A10 default process sampled before greedy generation; L4 starts greedy evaluation after smoke "
        "and the same warmup protocol. L4 requests and caps two CPU cores; A10 requested two and capped four. "
        "Findings do not cover other serving schedules, training seeds, native tool APIs, or executed code.\n"
    )
    args.out.write_text(article)
    args.report.write_text(report)
    manifest = {
        "sources_sha256": {
            str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in data["sources"].values()
        },
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "outputs_sha256": {
            str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (args.out, args.report)
        },
        "interval_status": "All confidence intervals in the article and report are exploratory.",
        "new_model_runs": 0,
        "default_winners": winner_rows(data),
    }
    args.manifest.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Rendered {args.out} and {args.report} from saved artifacts only.")


if __name__ == "__main__":
    main()
