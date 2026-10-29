# Batching changes 2–5% of greedy answers. One answer can swap the winner.

Changing batch size changed about 2–5% of greedy answers in my small-model study. For Llama3B and Qwen3-4B, that was enough to swap rank: the lead was one correct answer out of 500, inside exploratory paired 95% intervals of roughly ±3 percentage points. The flip is real in the recorded scores; it does not establish which model is better on new questions.

I tested tool calling: choosing the right function and supplying the right arguments. Six small models ran on an A10 GPU. I then repeated the two closest comparisons on L4 GPUs, keeping the same questions, model versions, prompts, and grading rules. Batch sizes were 1, 8, and 32.

Each table cell names the model with more correct answers. A tie means both scored the same. "Invariant" is vLLM's setting that removes dependence on the batch.

| GPU | Decoding | Batch 1 winner | Batch 8 winner | Batch 32 winner |
|---|---|---|---|---|
| A10 | Default | Qwen3-4B | Tie | Llama3B |
| L4 | Default | Llama3B | Tie | Qwen3-4B |
| A10 | Invariant | Llama3B | Llama3B | Llama3B |
| L4 | Invariant | Llama3B | Llama3B | Llama3B |

The default winner sequence reverses between GPUs. On A10, Qwen scores 458, 457, and 456 correct answers while Llama stays at 457. On L4, Llama scores 458, 457, and 458, while Qwen scores 457, 457, and 459. The second close pair, Qwen2.5-3B versus Qwen3-1.7B, never swaps order.

![Correct answers at each batch size, default and invariant, on A10 and L4](https://github.com/mohi-devhub/leaderboard-noise/blob/main/blog/rank-order-pair1.png?raw=true)

The figure zooms the vertical axis: each step is one correct answer, or 0.2 percentage points.

Greedy decoding always picks the token with the highest computed score. But changing a batch can change floating-point arithmetic. Near a token tie, a tiny numerical difference can change the chosen word and the rest of the answer. Changed text does not always change correctness, which is why a few changed answers need not overturn a clear lead.

Batch invariance removed the observed text changes. For all four models repeated on L4, the invariant outputs were also identical across A10 and L4. But switching it on can itself change the winner: A10's batch-1 lead moves from Qwen to Llama. Here, invariance stabilizes outputs; it does not choose the best answer.

That stability costs speed. Across the A10 configurations, median token throughput was 32–60% lower with invariance, measured with three repetitions per configuration.

The separate sampling analysis projects roughly 800–1,100 questions to resolve a 3-percentage-point gap, with ten sampled answers per question per model. The two close pairs need approximately 834 and 1,100 items. More answers to the same questions cannot replace broader question coverage.

If you compare models on your own evals, fix the batch size for every model or enable batch invariance for all of them. On a few hundred questions, don't trust gaps under about 3 percentage points as evidence that one model is better.

These findings cover a frozen BFCL subset and the recorded setups. All confidence intervals are exploratory; host settings, drivers, and generation history also differ between GPUs. I did not repeat throughput measurements on L4, and zero observed invariant changes is not a universal determinism guarantee.

The [full report](https://github.com/mohi-devhub/leaderboard-noise/blob/main/results/REPORT.md) includes every model pair, intervals, timings, and costs. The reusable `evalnoise` CLI applies the same uncertainty analysis to saved per-item results.
