# Partial study: one completed model

**The six-model study is incomplete.** Qwen2.5-1.5B finished; the app stopped before model two was accepted. No pairwise flip rate can be estimated from this single model. Saved outputs are retained and must not be rerun.

## Sampling accuracy

500 frozen BFCL items, temperature .7, n=10. Official BFCL scoring; 5,000 item-bootstrap draws.

| Metric | Estimate | Item-bootstrap 95% CI |
|---|---:|---|
| pass@1 | 79.36% | [76.36%, 82.30%] |
| pass@5 | 88.76% | [86.16%, 91.30%] |
| pass@10 | 91.00% | [88.40%, 93.40%] |

## Greedy sensitivity

| Arm | Text changed / 500 | Wilson 95% interval | Token IDs changed | Correctness changed | Scores at 1 / 8 / 32 |
|---|---:|---|---:|---:|---|
| default | 13 | [1.53%, 4.40%] | 15 | 0.8% | 81.2% / 81.2% / 81.4% |
| batch_invariant | 0 | [0.00%, 0.76%] | 0 | 0.0% | 80.8% / 80.8% / 80.8% |

## Three matched throughput repetitions

Ratios are invariant/default. These describe this A10 configuration, without a general production performance claim.

| Batch | Token-rate median | Token-rate range | Completion-rate median | Completion-rate range |
|---|---:|---|---:|---|
| serial | 0.562 | [0.553, 0.580] | 0.562 | [0.554, 0.581] |
| batch8 | 0.598 | [0.594, 0.624] | 0.598 | [0.594, 0.624] |
| batch32 | 0.678 | [0.672, 0.678] | 0.662 | [0.658, 0.679] |

## Time, cost, and limits

Execution took 2053.81s versus 2,072.68s forecast. Modal reports $0.75502874 in app-specific gross usage. The conservative stopped-app resource estimate plus setup/egress margin is $0.866595. Settled invoice actuals are unknown. Post-stop client waiting is excluded from compute cost.

All 9,800 saved predictions were scored, including 1,800 separate timing predictions. Truncations: 1. Timing rows never inflate primary accuracy samples. Text-change intervals assume independent items. These observations concern NVIDIA A10 and the pinned setup. They cannot establish six-model rankings or close-pair flip rates.

All evalnoise apps are stopped and holds released. qunti-check was not modified. The prepared remaining-five job requires approval because its forecast exceeds $5.
