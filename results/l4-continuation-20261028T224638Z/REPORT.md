# L4 follow-up alongside A10

Status: **complete**. Completed 4/4 models and scored 12,000 greedy predictions on the same 500 items, two arms, and batch sizes 1/8/32. Both pairs were selected before L4 outcomes. Missing models: none.

The A10 Llama3B/Qwen3-4B full-set strict batch flip **reproduced on this L4**. Exact strict/tied order pattern across batch sizes reproduced: False. This is one physical L4 replication, not a statement about every L4 or serving schedule.

## Full-set scores and bootstrap batch flips

Score cells give correct calls out of 500 at batch sizes 1 / 8 / 32. A strict flip requires opposite strict orders at two batch settings; ties are separate. Bootstrap fractions use 5,000 paired item draws, with exploratory outer 95% intervals from 500 outer and 1,000 inner draws. Collapsed intervals do not prove population certainty. Monte Carlo precision and paired score-difference intervals are retained in JSON. Intervals are unadjusted for multiple comparisons.

| Pair | GPU | Arm | Model A correct | Model B correct | Full-set strict flip | Bootstrap fraction [exploratory 95% interval] |
|---|---|---|---|---|---|---|
| Llama-3.2-3B-Instruct vs Qwen3-4B-Instruct-2507 | A10 | default | 457 / 457 / 457 | 458 / 457 / 456 | True | 8.94% [0.50%, 23.66%] |
| Llama-3.2-3B-Instruct vs Qwen3-4B-Instruct-2507 | A10 | batch_invariant | 458 / 458 / 458 | 457 / 457 / 457 | False | 0.00% [0.00%, 0.00%] |
| Llama-3.2-3B-Instruct vs Qwen3-4B-Instruct-2507 | L4 | default | 458 / 457 / 458 | 457 / 457 / 459 | True | 10.28% [1.10%, 27.81%] |
| Llama-3.2-3B-Instruct vs Qwen3-4B-Instruct-2507 | L4 | batch_invariant | 458 / 458 / 458 | 457 / 457 / 457 | False | 0.00% [0.00%, 0.00%] |
| Qwen2.5-3B-Instruct vs Qwen3-1.7B | A10 | default | 426 / 428 / 428 | 434 / 432 / 434 | False | 13.18% [0.60%, 35.80%] |
| Qwen2.5-3B-Instruct vs Qwen3-1.7B | A10 | batch_invariant | 423 / 423 / 423 | 433 / 433 / 433 | False | 0.00% [0.00%, 0.00%] |
| Qwen2.5-3B-Instruct vs Qwen3-1.7B | L4 | default | 427 / 428 / 428 | 432 / 433 / 434 | False | 8.48% [0.70%, 28.45%] |
| Qwen2.5-3B-Instruct vs Qwen3-1.7B | L4 | batch_invariant | 423 / 423 / 423 | 433 / 433 / 433 | False | 0.00% [0.00%, 0.00%] |

## Text changes across batch settings

Wilson 95% intervals assume independent items. The same 500 items recur across models and GPUs; do not pool them as independent questions.

| Model | GPU | Arm | Changed text / 500 | Rate [95% interval] | Changed correctness |
|---|---|---|---:|---|---:|
| Llama-3.2-3B-Instruct | A10 | default | 10 | 2.00% [1.09%, 3.64%] | 0 |
| Llama-3.2-3B-Instruct | A10 | batch_invariant | 0 | 0.00% [0.00%, 0.76%] | 0 |
| Llama-3.2-3B-Instruct | L4 | default | 12 | 2.40% [1.38%, 4.15%] | 2 |
| Llama-3.2-3B-Instruct | L4 | batch_invariant | 0 | 0.00% [0.00%, 0.76%] | 0 |
| Qwen3-4B-Instruct-2507 | A10 | default | 11 | 2.20% [1.23%, 3.90%] | 5 |
| Qwen3-4B-Instruct-2507 | A10 | batch_invariant | 0 | 0.00% [0.00%, 0.76%] | 0 |
| Qwen3-4B-Instruct-2507 | L4 | default | 12 | 2.40% [1.38%, 4.15%] | 5 |
| Qwen3-4B-Instruct-2507 | L4 | batch_invariant | 0 | 0.00% [0.00%, 0.76%] | 0 |
| Qwen2.5-3B-Instruct | A10 | default | 18 | 3.60% [2.29%, 5.62%] | 6 |
| Qwen2.5-3B-Instruct | A10 | batch_invariant | 0 | 0.00% [0.00%, 0.76%] | 0 |
| Qwen2.5-3B-Instruct | L4 | default | 23 | 4.60% [3.08%, 6.81%] | 8 |
| Qwen2.5-3B-Instruct | L4 | batch_invariant | 0 | 0.00% [0.00%, 0.76%] | 0 |
| Qwen3-1.7B | A10 | default | 13 | 2.60% [1.53%, 4.40%] | 6 |
| Qwen3-1.7B | A10 | batch_invariant | 0 | 0.00% [0.00%, 0.76%] | 0 |
| Qwen3-1.7B | L4 | default | 12 | 2.40% [1.38%, 4.15%] | 4 |
| Qwen3-1.7B | L4 | batch_invariant | 0 | 0.00% [0.00%, 0.76%] | 0 |

## Controls and interpretation

Validation matched every checkpoint revision, rendered/message hash, seed, inference package version, engine setting, and the Llama special-token correction with A10. Each process passed five smoke requests. The 4 completed models span 2 physical L4 cards. Every requested pair shares its card, and each model's arms stay on that device. The primary pair was preserved after preemption; only unfinished models resumed. Incorrect and truncated outputs remain in the denominator. Cross-GPU exact-text and correctness agreement at fixed batch settings are saved separately.

Length-truncated outputs: 0. No additional stochastic generation or repeated-throughput study was performed. A10's default process performed sampling before greedy evaluation; this focused follow-up starts greedy evaluation after smoke and the same per-condition warmup. Generation times support cost accounting; they are not a general performance comparison. The L4 worker requested and capped two CPU cores, versus the A10 worker's two-core request and four-core cap. Generation history, host/driver differences, and one card per GPU family within each pair prevent attributing every difference solely to GPU architecture. The A10 close pairs were exploratory there; this L4 follow-up preselected them before collecting L4 data.

## Cost and cleanup

Forecast $1.7891; app-specific gross metering $1.3009; conservative session estimate $1.5219. Whole-project estimate $10.7213/$12. The follow-up also has its own $5 cap. Metering is provisional and settled invoice actuals are unknown.

Across the initial allocation and continuation, total follow-up gross metering is $2.7296; conservative follow-up estimate $3.1575/$5, versus the original $3.6089 forecast. The continuation forecast is separate from that original whole-follow-up forecast. Preempted runtime is charged; post-preemption GPU queue waiting is excluded from resource time.

Owned apps stopped: True; owned running containers: 0; active reservations: $0.00. Checkpoints were SHA256-verified before volume deletion when complete. qunti-check was not modified. See receipt.json, job-result.json budget gates, forecast.json, billing-tagged.json, and download-receipt.json.
