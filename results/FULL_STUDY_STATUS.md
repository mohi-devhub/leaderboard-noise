# Completed six-model A10 study

All six models completed. Inference finished October 28, 2026, and analysis finalized October 29 in Asia/Kolkata, before the October 31 deadline. **Do not resubmit any job.**

The [full numerical report](REPORT.md), [article](../blog/STUDY.md), [figures](../figures/study-20261028T065939Z), and [receipt](study-20261028T065939Z/receipt.json) are complete. Official BFCL scoring covers 58,800 predictions: 48,000 primary and 10,800 separate timing outputs. Every planned cell was validated. The installed CLI reproduced the saved sampling analysis metrics exactly.

## Main findings

Default greedy text changes ranged from 2% to 4% per model across batch sizes 1, 8, and 32. Batch invariance produced zero observed text or correctness changes for every model. Each zero text-change estimate has Wilson 95% interval [0%, 0.76%] under the independent-item approximation.

Llama3B versus Qwen3-4B was the only observed full-set strict batch flip among 15 pairs. At batch sizes 1/8/32, Llama passed 457/457/457 items and Qwen passed 458/457/456. Invariance stabilized Llama at 458 and Qwen at 457. This removes observed batch sensitivity but does not establish a statistically separated population winner.

| Observed-close pair | Default batch-flip fraction | Exploratory outer-bootstrap 95% interval | Invariant fraction and interval |
|---|---:|---|---|
| Qwen2.5-3B vs Qwen3-1.7B | 13.18% | [0.60%, 35.80%] | 0% [0%, 0%], collapsed |
| Llama3B vs Qwen3-4B | 8.94% | [0.50%, 23.66%] | 0% [0%, 0%], collapsed |

Flip fractions describe paired item resampling. Ties are excluded; collapsed intervals do not establish population certainty. Both observed-close pairs share the same physical A10. The three pairs preselected using published scores were not within three points here; all are retained. Additional close-pair analysis is exploratory.

Median invariant/default token-rate ratios ranged from 0.400 to 0.678 across the 18 model/batch settings, about 32–60% lower throughput. Each setting has three matched repetitions; all ranges and completion-rate ratios are in the report. These are configuration measurements, without a general production performance recommendation.

## Cost and cleanup

The approved remaining-five forecast was $6.5151. App-specific provisional gross usage is $5.6008, with conservative resource estimate $6.3636. Whole-project conservative estimated spend is $7.5638 of $12, including setup failures and pilot. Settled invoice actuals are unknown. All reservations are released.

All evalnoise study apps are stopped, with zero running containers. Final app listing also showed no running unrelated app, but qunti-check was not stopped or modified by this project. The temporary results volume was deleted only after every checkpoint matched its committed SHA256.

The remaining-five continuation used one detached GPU call and per-model volume commits, preserving the original first model. A temporary local storage-read error required one observer reconnection, without a GPU resubmission. The first model used an earlier A10; every model's arms and timing repetitions stayed on its assigned physical device. Llama's corrected tokenization setting is verified in all six processes, with before/after source snapshots retained.

Local tests: 35 passed. Ruff lint and format checks passed on 36 project files. Dependency audit results and the narrowly approved setuptools applicability exceptions are documented in SECURITY.md. Final hashes and verification evidence are recorded in `metadata/verification.json`.
