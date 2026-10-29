# L4 follow-up complete

All four requested models and both arms completed on the same frozen 500 BFCL items, with 12,000 scored greedy outcomes at batch sizes 1/8/32. Every model/arm process passed its five-request smoke gate. There are no length truncations.

The **Llama3B/Qwen3-4B full-set flip reproduces on L4, in the opposite direction to A10**. A10 default correct counts were Llama 457/457/457 versus Qwen 458/457/456; L4 counts are 458/457/458 versus 457/457/459. Invariant counts on both GPUs are Llama 458/458/458 versus Qwen 457/457/457. These one-answer differences do not establish population superiority.

| Pair | A10 default bootstrap flip fraction [exploratory 95% interval] | L4 default fraction [exploratory 95% interval] | Full-set strict flips |
|---|---|---|---|
| Llama3B / Qwen3-4B | 8.94% [0.50%, 23.66%] | 10.28% [1.10%, 27.81%] | Both GPUs |
| Qwen2.5-3B / Qwen3-1.7B | 13.18% [0.60%, 35.80%] | 8.48% [0.70%, 28.45%] | Neither GPU |

Both pairs' invariant bootstrap fractions and outer intervals are zero on both GPUs. Collapsed intervals are not population certainty. Default L4 text changes were 2.4% for Llama, Qwen3-4B, and Qwen3-1.7B, and 4.6% for Qwen2.5-3B. Invariant text changes were zero for each model; the per-model Wilson upper bound is about 0.76%. Invariant text and correctness also match A10 exactly in all 12 model/condition cells.

The first L4 was preempted after the primary pair. Its 6,000 scored rows and model checkpoints were preserved byte for byte; only the unfinished pair resumed on a second L4. Each requested pair and both arms share one physical card. Uncheckpointed partial work is charged but not scored. The frozen revisions, prompt hashes, seeds, engine settings, inference versions, and Llama tokenization correction match A10. Host, driver, CPU-cap and generation-history differences limit a causal GPU-only interpretation. No additional throughput trials or stochastic samples were collected.

Original forecast $3.6089; combined provisional gross metering $2.7296; conservative follow-up estimate $3.1575/$5; project estimate $10.7213/$12. Invoice actuals remain unknown. Both apps stopped, zero owned running containers, all reservations released, both temporary volumes deleted after SHA256 verification. qunti-check was untouched.

Read the [article](../blog/STUDY.md), [full report](REPORT.md), [figures](../figures/l4-continuation-20261028T224638Z), and [receipt](l4-continuation-20261028T224638Z/receipt.json). The installed CLI exactly matches the report metrics. All 47 tests pass.
