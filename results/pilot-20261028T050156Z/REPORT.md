# Pilot report

Measured pilot only: two checkpoints, 100 frozen items. Full experiment awaits approval.
GPU: **NVIDIA A10** for every model and arm. Batch-invariance findings are restricted to this GPU and pinned software/configuration.

## Stochastic decoding

Temperature 0.7; ten generations/item. Paired item-bootstrap 95% intervals.

| Model | pass@1 | 95% CI | pass@5 | pass@10 |
|---|---:|---|---:|---:|
| Qwen/Qwen2.5-0.5B-Instruct | 0.519 | [0.441, 0.596] | 0.709 | 0.740 |
| Qwen/Qwen2.5-1.5B-Instruct | 0.839 | [0.780, 0.894] | 0.930 | 0.940 |

Strict bootstrap P(Qwen/Qwen2.5-0.5B-Instruct > Qwen/Qwen2.5-1.5B-Instruct) = 0.0000; tie mass 0.0000; rank-flip frequency 0.0. These are stability fractions, not posterior probabilities.

Approximate pass@1 MDD at this design: **0.1083** (fraction), two-sided alpha .05 and 80% power. This is a pilot-based projection, not a guaranteed detection threshold.

| Samples/item/model | Items for a .05 target gap | MDD at current N |
|---:|---:|---:|
| 1 | 917 | 0.1514 |
| 3 | 586 | 0.1210 |
| 5 | 520 | 0.1139 |
| 10 | 470 | 0.1083 |
| 20 | 445 | 0.1054 |

## Greedy batch intervention

| Arm | Model | Changed exact text | Changed correctness | Changed token IDs |
|---|---|---:|---:|---:|
| default | Qwen/Qwen2.5-0.5B-Instruct | 11.0% | 3.0% | 12.0% |
| default | Qwen/Qwen2.5-1.5B-Instruct | 3.0% | 0.0% | 3.0% |
| batch_invariant | Qwen/Qwen2.5-0.5B-Instruct | 0.0% | 0.0% | 0.0% |
| batch_invariant | Qwen/Qwen2.5-1.5B-Instruct | 0.0% | 0.0% | 0.0% |

| Arm | Batch size | Model A pass@1 | Model B pass@1 | A − B | Observed order |
|---|---:|---:|---:|---:|---|
| default | 1 | 0.600 | 0.850 | -0.250 | Qwen/Qwen2.5-0.5B-Instruct < Qwen/Qwen2.5-1.5B-Instruct |
| default | 8 | 0.600 | 0.850 | -0.250 | Qwen/Qwen2.5-0.5B-Instruct < Qwen/Qwen2.5-1.5B-Instruct |
| default | 32 | 0.620 | 0.850 | -0.230 | Qwen/Qwen2.5-0.5B-Instruct < Qwen/Qwen2.5-1.5B-Instruct |
| batch_invariant | 1 | 0.620 | 0.840 | -0.220 | Qwen/Qwen2.5-0.5B-Instruct < Qwen/Qwen2.5-1.5B-Instruct |
| batch_invariant | 8 | 0.620 | 0.840 | -0.220 | Qwen/Qwen2.5-0.5B-Instruct < Qwen/Qwen2.5-1.5B-Instruct |
| batch_invariant | 32 | 0.620 | 0.840 | -0.220 | Qwen/Qwen2.5-0.5B-Instruct < Qwen/Qwen2.5-1.5B-Instruct |

default: strict observed ranking reversal across batch configurations = **False**.


batch_invariant: strict observed ranking reversal across batch configurations = **False**.

## Warm throughput and startup

| Model | Arm | Batch | Tokens/s | Completions/s | Decode seconds | Warmup seconds |
|---|---|---|---:|---:|---:|---:|
| Qwen/Qwen2.5-0.5B-Instruct | default | sampling | 1866.18 | 47.42 | 21.09 | 2.31 |
| Qwen/Qwen2.5-0.5B-Instruct | default | serial | 78.28 | 2.05 | 48.71 | 0.19 |
| Qwen/Qwen2.5-0.5B-Instruct | default | batch8 | 339.22 | 8.89 | 11.25 | 0.44 |
| Qwen/Qwen2.5-0.5B-Instruct | default | batch32 | 757.20 | 19.63 | 5.10 | 0.59 |
| Qwen/Qwen2.5-0.5B-Instruct | batch_invariant | serial | 56.38 | 1.46 | 68.33 | 0.67 |
| Qwen/Qwen2.5-0.5B-Instruct | batch_invariant | batch8 | 253.57 | 6.58 | 15.19 | 0.59 |
| Qwen/Qwen2.5-0.5B-Instruct | batch_invariant | batch32 | 558.82 | 14.51 | 6.89 | 0.77 |
| Qwen/Qwen2.5-1.5B-Instruct | default | sampling | 1023.94 | 27.04 | 36.98 | 4.04 |
| Qwen/Qwen2.5-1.5B-Instruct | default | serial | 67.41 | 1.75 | 56.99 | 0.21 |
| Qwen/Qwen2.5-1.5B-Instruct | default | batch8 | 273.25 | 7.12 | 14.05 | 0.59 |
| Qwen/Qwen2.5-1.5B-Instruct | default | batch32 | 538.94 | 14.36 | 6.96 | 1.04 |
| Qwen/Qwen2.5-1.5B-Instruct | batch_invariant | serial | 38.50 | 1.00 | 99.67 | 0.36 |
| Qwen/Qwen2.5-1.5B-Instruct | batch_invariant | batch8 | 167.78 | 4.37 | 22.87 | 0.94 |
| Qwen/Qwen2.5-1.5B-Instruct | batch_invariant | batch32 | 368.17 | 9.60 | 10.42 | 1.44 |

| Model | Configuration | Fix/default tokens/s ratio | Fix/default completions/s ratio |
|---|---|---:|---:|
| Qwen/Qwen2.5-0.5B-Instruct | serial | 0.720 | 0.713 |
| Qwen/Qwen2.5-0.5B-Instruct | batch8 | 0.748 | 0.741 |
| Qwen/Qwen2.5-0.5B-Instruct | batch32 | 0.738 | 0.739 |
| Qwen/Qwen2.5-1.5B-Instruct | serial | 0.571 | 0.572 |
| Qwen/Qwen2.5-1.5B-Instruct | batch8 | 0.614 | 0.614 |
| Qwen/Qwen2.5-1.5B-Instruct | batch32 | 0.683 | 0.668 |

Ratios below one indicate slower mitigation. Token throughput also depends on output length; inspect both rates. One timing per configuration and fixed baseline-first order cannot establish a precise general throughput penalty.

- Qwen/Qwen2.5-0.5B-Instruct / default: startup 11.72s, five smoke requests 0.25s.
- Qwen/Qwen2.5-0.5B-Instruct / batch_invariant: startup 11.64s, five smoke requests 1.40s.
- Qwen/Qwen2.5-1.5B-Instruct / default: startup 22.37s, five smoke requests 0.27s.
- Qwen/Qwen2.5-1.5B-Instruct / batch_invariant: startup 11.39s, five smoke requests 0.31s.

Length-truncated benchmark completions: 0/3200; retained and scored.

## Data quality

| Model | Condition | Predictions | Syntax/format failures | Truncated |
|---|---|---:|---:|---:|
| Qwen/Qwen2.5-0.5B-Instruct | sampling | 1000 | 83 | 0 |
| Qwen/Qwen2.5-0.5B-Instruct | default:serial | 100 | 3 | 0 |
| Qwen/Qwen2.5-0.5B-Instruct | default:batch8 | 100 | 4 | 0 |
| Qwen/Qwen2.5-0.5B-Instruct | default:batch32 | 100 | 3 | 0 |
| Qwen/Qwen2.5-0.5B-Instruct | batch_invariant:serial | 100 | 3 | 0 |
| Qwen/Qwen2.5-0.5B-Instruct | batch_invariant:batch8 | 100 | 3 | 0 |
| Qwen/Qwen2.5-0.5B-Instruct | batch_invariant:batch32 | 100 | 3 | 0 |
| Qwen/Qwen2.5-1.5B-Instruct | sampling | 1000 | 10 | 0 |
| Qwen/Qwen2.5-1.5B-Instruct | default:serial | 100 | 0 | 0 |
| Qwen/Qwen2.5-1.5B-Instruct | default:batch8 | 100 | 0 | 0 |
| Qwen/Qwen2.5-1.5B-Instruct | default:batch32 | 100 | 0 | 0 |
| Qwen/Qwen2.5-1.5B-Instruct | batch_invariant:serial | 100 | 0 | 0 |
| Qwen/Qwen2.5-1.5B-Instruct | batch_invariant:batch8 | 100 | 0 | 0 |
| Qwen/Qwen2.5-1.5B-Instruct | batch_invariant:batch32 | 100 | 0 | 0 |

## Cost and limitations

See BUDGET.md and this session's billing snapshots. Gross metered-account change is not necessarily project-specific or settled. Reservations are not invoice actuals. No full-run launch is authorized by this report.

Output disagreement need not imply score or rank disagreement. Absence of pilot flips does not prove batch invariance is unnecessary. Question dependence, small sample size, boundary bootstrap behavior and fixed arm order limit conclusions. No claim is made about other GPUs, training seeds, native tool APIs, or the complete BFCL leaderboard.

<!-- receipt:start -->
## Session cost and timing

- GPU: **NVIDIA A10**, one job and one container for every arm/model; no GPU comparisons are inferred.
- Five initial smoke requests passed before the 3,200 benchmark predictions. Each model/arm also passed its own internal smoke check.
- Remote execution: **591.57 seconds** (9.86 minutes), including imports, model loads, smoke tests, warmups, and generation.
- Observed container startup: **10.02 seconds**; controller wall time before cleanup: **636.74 seconds**.
- Connection reconnects used: **0**. Exactly one job was submitted.
- Resource-ceiling estimate: **$0.237615**, using execution + startup + two seconds of scaledown at 1.41720 USD/hour. Image building and egress are outside that timed estimate.
- Account gross-metered change: **$0.26244345**. The conservative session estimate uses the larger value: **$0.262443**. Attribution is provisional because account metering may lag or include unrelated usage. Settled invoice actuals remain unknown.
- Recorded estimated project total including prior failures: **$0.303541** of the $12 cap. The $4.50 unused reservation is released; active reservations are zero.

The evalnoise app is stopped. The separate qunti-check project was not modified. This pilot completed before the October 31 deadline. The full six-model experiment remains unapproved and has not been launched.
<!-- receipt:end -->
