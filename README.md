# leaderboard-noise: 2–5% of greedy answers change with batching

Batch size changed about 2–5% of greedy answers. For the near-tied Llama3B/Qwen3-4B pair, the observed flip was a one-item margin out of 500, within exploratory paired 95% intervals of roughly ±3 percentage points. The separate sampling analysis projects roughly 800–1,100 items to resolve a 3-point gap, with ten sampled answers per item per model.

Under batch invariance, decoded outputs were identical across A10 and L4 for all four replicated models. Switching to invariance can itself change the winner: at A10 batch 1, the lead moves from Qwen3-4B to Llama3B. Median token throughput was 32–60% lower in the repeated A10 timing study.

This project combines a six-model A10 study and a four-model L4 replication on 500 frozen BFCL items, with 70,800 scored outputs including timing repetitions. The reusable CLI remains `evalnoise`. All research confidence intervals are exploratory. L4 has no repeated throughput measurement.

Read the [merged article](blog/STUDY.md), [combined numerical report](results/REPORT.md), [A10 figures](figures/study-20261028T065939Z), [A10/L4 comparison figures](figures/l4-continuation-20261028T224638Z), and [selection rationale](docs/FULL_STUDY_PLAN.md). The article and report name the higher-ranked model at every default batch size on each GPU. The A10 published-score preselection separated more than expected; the two pairs found close on A10 were preselected for L4.

The conservative whole-project estimate is $10.7213/$12. L4 follow-up gross metering is $2.7296 provisional, against its original $3.6089 forecast; its conservative estimate is $3.1575/$5. Settled invoices remain unknown. All owned apps are stopped, holds released, and temporary results volumes deleted after verified downloads. qunti-check was untouched. See [budget](BUDGET.md) and the [final receipt](results/l4-continuation-20261028T224638Z/receipt.json).

This is a practical replication and analysis tool, not a new statistical method. See [related work](docs/RELATED_WORK.md), [methods](docs/METHODS.md), [learning notes](LEARNING.md), [security](SECURITY.md), and [decisions](DECISIONS.md). The [short post](blog/POST.md) summarizes the completed study. The [two-model pilot](results/pilot-20261028T050156Z/REPORT.md) remains historical. Optional code execution was not run.

## Install and analyze

Python >=3.12 and uv. All dependencies resolve from official PyPI; `uv.lock` includes artifact hashes.

```sh
UV_CACHE_DIR=.uv-cache UV_HTTP_TIMEOUT=120 uv sync --frozen --group modal
.venv/bin/evalnoise analyze results.jsonl --k 1 5 10 --output analysis.json
.venv/bin/evalnoise analyze results.jsonl --gap 0.03 --power 0.8 --format json
.venv/bin/python scripts/figures.py analysis.json --out figures/my-eval
.venv/bin/pytest -q
```

Default `--k 1` works with one prediction/item. Pass@5/10 require at least 5/10 predictions for every item. The CLI never executes supplied code or calls a model. It handles binary outcomes from any evaluator after explicit schema mapping; it does not infer correctness from arbitrary text. See [schema and adapters](docs/SCHEMA.md).

Two example aggregate rows (add at least two aligned items per model):

```json
{"model":"A","item_id":"q1","successes":[true,false,true]}
{"model":"B","item_id":"q1","successes":[false,false,true]}
```

For sample rows with different field names:

```sh
.venv/bin/evalnoise analyze input.jsonl --model-key model_name --item-key task_id --sample-key attempt --score-key grading.passed
```

Default: 5,000 resamples, fixed seed 20261101, 95% percentile CIs. The `items` report resamples matched item vectors. The `sampling` report resamples outcomes conditional on the same fixed items. Do not add their variances. Pairwise probabilities are strict bootstrap win fractions, with ties separate; they are not posterior probabilities. Planning is a pilot-based normal approximation for pass@1, default two-sided alpha=.05 and power=.8. See methods for assumptions, finite-repeat correction, dependence limitations, and boundary behavior.

## Regenerate the combined article and report

From the `leaderboard-noise` directory, run:

```sh
.venv/bin/python scripts/write_study_article.py
```

This local command reads saved A10 and L4 summaries and regenerates `blog/STUDY.md`, `results/REPORT.md`, and the source-hash and winner manifest `results/combined-sources.json`. It does not contact Modal, regrade answers, or launch inference. All 15 A10 pairs remain in the combined report, including null and preselected comparisons. Raw per-session reports, model outputs, receipts, and source snapshots remain frozen provenance.

To recreate the existing figures from saved summaries:

```sh
MPLCONFIGDIR=.uv-cache/matplotlib .venv/bin/python scripts/study_figures.py results/study-20261028T065939Z --out figures/study-20261028T065939Z
MPLCONFIGDIR=.uv-cache/matplotlib .venv/bin/python scripts/l4_figures.py results/l4-continuation-20261028T224638Z --out figures/l4-continuation-20261028T224638Z
```

The original pilot commands below document its historical protocol and approval gates. They are separate from regenerating the completed study's documents.

## Prepare and run the pilot

Separate CPU BFCL and GPU environments avoid upstream numpy/tree-sitter conflicts. `experiments/models.json` pins all six candidate checkpoints. The GPU lock targets Linux x86_64, Python 3.12; the CPU BFCL lock targets macOS arm64 Python 3.12 in this workspace.

```sh
UV_CACHE_DIR=.uv-cache UV_HTTP_TIMEOUT=120 uv venv .venv-bfcl --python 3.12
UV_CACHE_DIR=.uv-cache UV_HTTP_TIMEOUT=120 uv pip sync --python .venv-bfcl/bin/python --require-hashes experiments/bfcl.lock
.venv-bfcl/bin/python scripts/bfcl_smoke.py
.venv-bfcl/bin/python scripts/prepare_bfcl.py
.venv/bin/python scripts/run_pilot.py
.venv/bin/python scripts/run_pilot.py --execute
.venv/bin/python scripts/report_pilot.py results/pilot-TIMESTAMP
.venv/bin/python scripts/figures.py results/pilot-TIMESTAMP/analysis-sampling.json --out figures/pilot
```

Run the audit commands in SECURITY.md before launch. The GPU image installs only hash-verified wheels from PyPI and audits its actual Python packages before GPU work. Two setuptools build/install advisories have explicit user-approved applicability exceptions; no unaccepted findings are permitted. Model inference disables remote model code. Five smoke requests precede benchmark generation in each model/arm process. Raw outputs, token IDs, frozen prompt hashes, immutable model revisions, timing and installed-package metadata are retained.

The corrected image adds Debian `build-essential=12.12` and passes a CPU compiler/headers preflight. Each authorized attempt is guarded by `experiments/pilot.json`. Cleanup always targets only this evalnoise app ID; unrelated projects are preserved. App tags identify `project=evalnoise` and the session for billing reports; they do not retroactively attribute earlier untagged attempts.

`run_pilot.py` reserves $4.50 against the $12 cap and does not launch the six-model experiment. The October 28 authorization uses one detached, 90-minute-bounded job with ordered L4/A10 allocation, one five-request smoke gate, and all model/arm stages in the same container. The saved call ID permits one fresh-connection reattachment; it is never resubmitted. Worker failures stop the run. Cleanup in `finally` stops only this app. After scoring, read the pilot report and BUDGET.md and obtain the user's OK before any full run. No automatic scheduled run is installed.

The baseline collects 10 samples at temperature .7, then three greedy request batch sizes (1/8/32). The fix arm repeats those three greedy configurations with `VLLM_BATCH_INVARIANT=1`. Both use the same max engine concurrency (64), same eager execution and no prefix cache. This tests batch sensitivity with controlled offline inference submission, not a production HTTP load generator. The official BFCL prompting-mode instructions and AST checker define correctness. Scores are for a selected Python single-turn subset, not the complete leaderboard.

Generated model code for optional EvalPlus must execute on isolated CPU infrastructure, with no secrets or writable host mounts. `experiments/evalplus.in` is the optional dependency entry point; no code benchmark is launched by the pilot. The full model/benchmark plan stays in scope and needs a measured budget estimate after pilot review.
