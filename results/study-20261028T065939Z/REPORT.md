# Six-model BFCL study

Completed evaluation on **NVIDIA A10**. The preserved first model used one device; the remaining five shared a second device after the infrastructure interruption. Every model's two arms and timing repetitions stayed on its assigned GPU. Exact names and UUIDs are in summary.json; conclusions are restricted to this recorded A10 setup. 48,000 primary predictions and 10,800 separate timing predictions were scored with the official BFCL harness.

## Selection rationale

The user approved a new roster targeting close scores. The pilot's 32-point Qwen0.5B/1.5B sampling gap excluded 0.5B. Qwen1.5B remains the measured anchor, joined by Qwen2.5-3B, Qwen3-1.7B, Llama3.2-3B, xLAM2-3B, and Qwen3-4B-Instruct-2507. Published non-live AST scores preselected Qwen3-1.7B/Llama3B/xLAM3B, with gaps 0.25/0.04/0.29 points. Their published FC scores guide selection but do not reproduce this common-prompting Python subset. No model or item was replaced after full-study results. [Frozen plan](../../docs/FULL_STUDY_PLAN.md), [official leaderboard source](https://gorilla.cs.berkeley.edu/data_overall.csv).

Observed default-serial gaps at most three points: **2/15 pairs**. Preselected pairs remain reported even when not close on this task. Additional close-pair labels are exploratory selection on these data.

## Sampling accuracy

Temperature .7, n=10; 500 paired items, 5,000 item-bootstrap resamples. Timing repetitions do not increase this sample count.

| Model | pass@1 | 95% item CI | pass@5 | pass@10 |
|---|---:|---|---:|---:|
| Qwen2.5-1.5B-Instruct | 79.36% | [76.36%, 82.30%] | 88.76% | 91.00% |
| Qwen2.5-3B-Instruct | 83.58% | [80.56%, 86.48%] | 89.33% | 91.00% |
| Qwen3-1.7B | 86.48% | [83.72%, 89.16%] | 89.55% | 90.00% |
| Llama-3.2-3B-Instruct | 89.12% | [86.78%, 91.32%] | 94.08% | 95.20% |
| xLAM-2-3b-fc-r | 74.50% | [71.32%, 77.70%] | 84.32% | 87.40% |
| Qwen3-4B-Instruct-2507 | 91.30% | [88.94%, 93.50%] | 94.03% | 95.20% |

## Pairwise flip rates and uncertainty

A batch flip means at least two batch settings give opposite strict orders in the same paired item resample. Ties are separate and do not count as flips. The fraction concerns resampling stability, not a posterior probability. Sampling flips reverse the fixed observed sampling order.

Intervals below are exploratory outer item-bootstrap percentile ranges, with 500 outer and 1,000 inner draws. They can collapse at ties/boundaries and with absent empirical patterns, and include inner Monte Carlo error. They are not simultaneous or guaranteed-calibrated population intervals. Separate Wilson intervals in JSON quantify only finite Monte Carlo precision conditional on these observed data. Inspect paired score-difference CIs alongside flip fractions.

| Pair | Preselected / observed close | Arm | Actual full-set batch flip | Bootstrap flip fraction | Exploratory 95% interval |
|---|---|---|---|---:|---|
| Qwen2.5-3B-Instruct vs Qwen3-1.7B | False / True | default | False | 13.18% | [0.60%, 35.80%] |
| Qwen2.5-3B-Instruct vs Qwen3-1.7B | False / True | batch_invariant | False | 0.00% | [0.00%, 0.00%] |
| Qwen2.5-3B-Instruct vs Qwen3-1.7B | False / True | sampling | n/a | 3.44% | [0.00%, 53.00%] |
| Qwen3-1.7B vs Llama-3.2-3B-Instruct | True / False | default | False | 0.14% | [0.00%, 7.30%] |
| Qwen3-1.7B vs Llama-3.2-3B-Instruct | True / False | batch_invariant | False | 0.00% | [0.00%, 0.00%] |
| Qwen3-1.7B vs Llama-3.2-3B-Instruct | True / False | sampling | n/a | 2.54% | [0.00%, 51.51%] |
| Qwen3-1.7B vs xLAM-2-3b-fc-r | True / False | default | False | 0.00% | [0.00%, 0.00%] |
| Qwen3-1.7B vs xLAM-2-3b-fc-r | True / False | batch_invariant | False | 0.00% | [0.00%, 0.00%] |
| Qwen3-1.7B vs xLAM-2-3b-fc-r | True / False | sampling | n/a | 0.00% | [0.00%, 0.00%] |
| Llama-3.2-3B-Instruct vs xLAM-2-3b-fc-r | True / False | default | False | 0.00% | [0.00%, 0.00%] |
| Llama-3.2-3B-Instruct vs xLAM-2-3b-fc-r | True / False | batch_invariant | False | 0.00% | [0.00%, 0.00%] |
| Llama-3.2-3B-Instruct vs xLAM-2-3b-fc-r | True / False | sampling | n/a | 0.00% | [0.00%, 0.00%] |
| Llama-3.2-3B-Instruct vs Qwen3-4B-Instruct-2507 | False / True | default | True | 8.94% | [0.50%, 23.66%] |
| Llama-3.2-3B-Instruct vs Qwen3-4B-Instruct-2507 | False / True | batch_invariant | False | 0.00% | [0.00%, 0.00%] |
| Llama-3.2-3B-Instruct vs Qwen3-4B-Instruct-2507 | False / True | sampling | n/a | 5.58% | [0.00%, 63.16%] |

All 15 comparisons, including non-close pairs, are in [pairwise-flips.json](pairwise-flips.json) and [CSV](pairwise-flips.csv). Complete score-difference intervals, bootstrap win/tie fractions, rank distributions, and MDD/item/sample projections are in the condition-specific analysis JSON files.

| Pair, A minus B | Default serial gap | Paired item-bootstrap 95% gap CI | Same physical A10 |
|---|---:|---|---|
| Qwen2.5-3B-Instruct vs Qwen3-1.7B | -1.60% | [-5.20%, 1.80%] | True |
| Qwen3-1.7B vs Llama-3.2-3B-Instruct | -4.60% | [-7.60%, -1.60%] | True |
| Qwen3-1.7B vs xLAM-2-3b-fc-r | 11.40% | [7.60%, 15.20%] | True |
| Llama-3.2-3B-Instruct vs xLAM-2-3b-fc-r | 16.00% | [11.80%, 20.20%] | True |
| Llama-3.2-3B-Instruct vs Qwen3-4B-Instruct-2507 | -0.20% | [-3.20%, 2.80%] | True |

## Planning for a three-point gap

Normal-approximation projections use the stochastic pass@1 paired variance components, two-sided alpha .05, and 80% power. They assume independent questions and iid model generations. They are planning estimates, not guarantees of significance for another evaluation or pair.

| Pair | Current MDD, 500 items × 10 samples/model | Projected items for a .03 gap at 10 samples/model |
|---|---:|---:|
| Qwen2.5-3B-Instruct vs Qwen3-1.7B | 4.45% | 1100 |
| Qwen3-1.7B vs Llama-3.2-3B-Instruct | 3.94% | 863 |
| Qwen3-1.7B vs xLAM-2-3b-fc-r | 4.84% | 1300 |
| Llama-3.2-3B-Instruct vs xLAM-2-3b-fc-r | 4.76% | 1257 |
| Llama-3.2-3B-Instruct vs Qwen3-4B-Instruct-2507 | 3.87% | 834 |

## Greedy changes

| Model | Arm | Changed text / 500 | Wilson 95% interval | Changed token IDs | Changed correctness | Scores at batches 1 / 8 / 32 |
|---|---|---:|---|---:|---:|---|
| Qwen2.5-1.5B-Instruct | default | 13 | [1.53%, 4.40%] | 15 | 4 | 81.20% / 81.20% / 81.40% |
| Qwen2.5-1.5B-Instruct | batch_invariant | 0 | [0.00%, 0.76%] | 0 | 0 | 80.80% / 80.80% / 80.80% |
| Qwen2.5-3B-Instruct | default | 18 | [2.29%, 5.62%] | 19 | 6 | 85.20% / 85.60% / 85.60% |
| Qwen2.5-3B-Instruct | batch_invariant | 0 | [0.00%, 0.76%] | 0 | 0 | 84.60% / 84.60% / 84.60% |
| Qwen3-1.7B | default | 13 | [1.53%, 4.40%] | 15 | 6 | 86.80% / 86.40% / 86.80% |
| Qwen3-1.7B | batch_invariant | 0 | [0.00%, 0.76%] | 0 | 0 | 86.60% / 86.60% / 86.60% |
| Llama-3.2-3B-Instruct | default | 10 | [1.09%, 3.64%] | 10 | 0 | 91.40% / 91.40% / 91.40% |
| Llama-3.2-3B-Instruct | batch_invariant | 0 | [0.00%, 0.76%] | 0 | 0 | 91.60% / 91.60% / 91.60% |
| xLAM-2-3b-fc-r | default | 20 | [2.60%, 6.10%] | 20 | 4 | 75.40% / 75.40% / 75.60% |
| xLAM-2-3b-fc-r | batch_invariant | 0 | [0.00%, 0.76%] | 0 | 0 | 75.40% / 75.40% / 75.40% |
| Qwen3-4B-Instruct-2507 | default | 11 | [1.23%, 3.90%] | 13 | 5 | 91.60% / 91.40% / 91.20% |
| Qwen3-4B-Instruct-2507 | batch_invariant | 0 | [0.00%, 0.76%] | 0 | 0 | 91.40% / 91.40% / 91.40% |

Wilson intervals assume independent items; shared functions/templates can violate that assumption. Repeat-to-repeat timing output checks are saved separately. Stabilizing text does not imply improved accuracy.

Changing the mitigation setting itself strictly reversed 1 pairwise full-set orders at one or more fixed batch sizes. This is separate from batch-induced instability within an arm. Details, including transitions involving ties, are in each pair's `mitigation_order_changes` field.

## Repeated throughput

Three matched repetitions use the same 100 items in each configuration, alternating arm order between repetitions. Values are fix/default ratios. Ratios below one mean lower invariant throughput. Output length affects tokens/s, so completions/s and elapsed-time ratios are also retained. Initialization and warmup are excluded here but included in cost.

| Model | Batch configuration | Median token-rate ratio | Range, three repetitions | Median completion-rate ratio | Completion-rate range |
|---|---|---:|---|---:|---|
| Qwen2.5-1.5B-Instruct | serial | 0.562 | [0.553, 0.580] | 0.562 | [0.554, 0.581] |
| Qwen2.5-1.5B-Instruct | batch8 | 0.598 | [0.594, 0.624] | 0.598 | [0.594, 0.624] |
| Qwen2.5-1.5B-Instruct | batch32 | 0.678 | [0.672, 0.678] | 0.662 | [0.658, 0.679] |
| Qwen2.5-3B-Instruct | serial | 0.424 | [0.421, 0.433] | 0.422 | [0.419, 0.431] |
| Qwen2.5-3B-Instruct | batch8 | 0.490 | [0.488, 0.490] | 0.493 | [0.491, 0.493] |
| Qwen2.5-3B-Instruct | batch32 | 0.568 | [0.566, 0.570] | 0.574 | [0.572, 0.576] |
| Qwen3-1.7B | serial | 0.589 | [0.584, 0.600] | 0.585 | [0.580, 0.595] |
| Qwen3-1.7B | batch8 | 0.619 | [0.611, 0.620] | 0.614 | [0.606, 0.615] |
| Qwen3-1.7B | batch32 | 0.652 | [0.650, 0.662] | 0.650 | [0.647, 0.657] |
| Llama-3.2-3B-Instruct | serial | 0.406 | [0.404, 0.406] | 0.406 | [0.404, 0.406] |
| Llama-3.2-3B-Instruct | batch8 | 0.478 | [0.478, 0.480] | 0.479 | [0.478, 0.481] |
| Llama-3.2-3B-Instruct | batch32 | 0.586 | [0.585, 0.588] | 0.587 | [0.587, 0.590] |
| xLAM-2-3b-fc-r | serial | 0.426 | [0.422, 0.427] | 0.427 | [0.424, 0.429] |
| xLAM-2-3b-fc-r | batch8 | 0.499 | [0.494, 0.500] | 0.499 | [0.494, 0.500] |
| xLAM-2-3b-fc-r | batch32 | 0.578 | [0.575, 0.578] | 0.573 | [0.573, 0.577] |
| Qwen3-4B-Instruct-2507 | serial | 0.400 | [0.399, 0.405] | 0.399 | [0.399, 0.404] |
| Qwen3-4B-Instruct-2507 | batch8 | 0.475 | [0.474, 0.480] | 0.475 | [0.473, 0.479] |
| Qwen3-4B-Instruct-2507 | batch32 | 0.571 | [0.569, 0.573] | 0.570 | [0.568, 0.572] |

These are measured configuration overheads with three repetitions, not a general performance recommendation. No limiter profile or production tuning study was conducted. Full timings, generated-token counts, completion counts, driver, host load, and installed versions are retained in model artifacts.

## Data quality and scope

Total scored: 58,800; length-truncated: 17; AST syntax/format failures: 913. Every planned cell was validated. Incorrect and truncated model outputs remain in the denominator. Timing rows are scored to detect fast failures but do not enter primary accuracy or rank calculations.

This is the frozen Python single-turn subset, not the official overall leaderboard. Findings concern greedy batching on this GPU, pinned software, common prompts, and fixed decoding limits. They do not cover training-seed sensitivity, other GPUs, native tool APIs, code execution, or all possible serving schedules. Intervals are exploratory and unadjusted for multiple comparisons. Null results are retained.

## Cost and shutdown

See receipt.json, budget-checks.json, forecast.json, and BUDGET.md for measured resource time versus forecast, metering attribution, reservations, and invoice status. Account-wide deltas include unrelated qunti-check use and are not project costs. Cleanup targets only evalnoise. The prior pilot ran on a separately recorded GPU and is not pooled with this experiment.

<!-- receipt:start -->
## Cost, timing, and cleanup

The full-study forecast was $7.3310; the approved remaining-five forecast was $6.5151. Model one was preserved. The other five completed in one detached A10 GPU call with a server-side controller and volume checkpoints. Model execution totalled 17845.29 seconds.

| Model | Device | Forecast seconds | Measured seconds | Forecast GPU/resource cost | Measured execution resource ceiling |
|---|---|---:|---:|---:|---:|
| Qwen2.5-1.5B-Instruct | NVIDIA A10 | 2072.68 | 2053.81 | $0.8159 | $0.8085 |
| Qwen2.5-3B-Instruct | NVIDIA A10 | 3196.29 | 3282.43 | $1.2583 | $1.2922 |
| Qwen3-1.7B | NVIDIA A10 | 2447.22 | 2322.73 | $0.9634 | $0.9144 |
| Llama-3.2-3B-Instruct | NVIDIA A10 | 3196.29 | 3052.70 | $1.2583 | $1.2017 |
| xLAM-2-3b-fc-r | NVIDIA A10 | 3196.29 | 3098.51 | $1.2583 | $1.2198 |
| Qwen3-4B-Instruct-2507 | NVIDIA A10 | 4132.63 | 4035.09 | $1.6269 | $1.5885 |

Modal currently reports $5.600780 in app-specific gross metering for the remaining job, versus $6.5151 forecast. All study apps together report $6.355951. The conservative recorded study estimate is $7.240230; cumulative project estimate including earlier attempts is $7.563771/$12. Metering remains provisional and invoice actuals unknown. Account-wide deltas are excluded because qunti-check ran in parallel.

The first model and the continuation used two recorded A10 devices. Every model retained the same device across arms and timing repetitions. Exact names and UUIDs appear in summary.json and receipt.json. Preselected comparisons among the continuation models share their physical device. Cross-device anchor comparisons must be read with that limitation.

All evalnoise study apps are stopped and have zero running containers. Reservations are released. The temporary results volume was deleted only after every downloaded artifact matched its recorded SHA256. qunti-check was not modified. See remaining-job-result.json, remaining-download-receipt.json, remaining-billing-tagged.json, and the per-model budget logs for evidence.
<!-- receipt:end -->
