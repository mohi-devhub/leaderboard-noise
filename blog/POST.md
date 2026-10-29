# Default answers vary across batch settings and runs. One-item leads reverse.

Default decoding changed about 2–5% of greedy answers across batch settings in my small-model study. Same-batch repeats also varied, so this measures batch-setting plus run-to-run variation under default decoding. Qwen3-4B changed text and correctness on `parallel_multiple_37` between A10 timing repeats at the same batch size. Each untied Llama3B/Qwen3-4B lead is one correct answer out of 500; the reversal is a two-answer net swing. Those leads sit inside exploratory paired 95% intervals of roughly ±3 percentage points.

I tested tool calling: choosing functions and arguments. Six small models ran on A10. I repeated the two closest comparisons on L4, retaining the questions, checkpoints, prompts, and grading. Greedy batch sizes were 1, 8, and 32.

Each cell names the model with more correct answers. "Invariant" is vLLM's batch-invariance setting.

| GPU | Decoding | Batch 1 winner | Batch 8 winner | Batch 32 winner |
|---|---|---|---|---|
| A10 | Default | Qwen3-4B | Tie | Llama3B |
| L4 | Default | Llama3B | Tie | Qwen3-4B |
| A10 | Invariant | Llama3B | Llama3B | Llama3B |
| L4 | Invariant | Llama3B | Llama3B | Llama3B |

The default winner sequence reverses between GPUs. On A10, Qwen scores 458, 457, and 456 correct answers while Llama stays at 457. On L4, Llama scores 458, 457, and 458, while Qwen scores 457, 457, and 459. Qwen2.5-3B versus Qwen3-1.7B never swaps order.

![Correct answers at each batch size, default and invariant, on A10 and L4](https://github.com/mohi-devhub/leaderboard-noise/blob/main/blog/rank-order-pair1.png?raw=true)

The figure zooms the vertical axis: each step is one correct answer, or 0.2 percentage points.

Greedy decoding picks the token with the highest computed score. Batch shape can change floating-point arithmetic. Near a token tie, a tiny difference can change the chosen word and the answer. Changed text does not always change correctness.

Batch invariance removed all observed text changes across batch settings and timing repeats. For all four models repeated on L4, invariant outputs were identical across A10 and L4. Switching it on can itself change the winner: A10's batch-1 lead moves from Qwen to Llama. Stability does not choose the best answer.

Across A10 configurations, median token throughput was 32–60% lower with invariance, measured with three repetitions per configuration.

The separate sampling analysis projects roughly 800–1,100 questions to resolve a 3-percentage-point gap, with ten sampled answers per question per model. The close pairs need approximately 834 and 1,100 items. More answers to the same questions cannot replace broader question coverage.

For your own evals, use the same batch size for every model and repeat default runs, or enable batch invariance throughout. A fixed batch size alone did not ensure stable outputs here. On a few hundred questions, don't trust gaps under about 3 percentage points as evidence that one model is better.

These findings cover the frozen BFCL subset and recorded setups. All intervals are exploratory and unadjusted. CPU limits and generation history differ; hosts are uncontrolled, while retained driver versions match. I did not repeat throughput measurements on L4, and zero observed invariant changes is not a universal guarantee.

The [full report](https://github.com/mohi-devhub/leaderboard-noise/blob/main/results/REPORT.md) includes every pair, intervals, timings, and costs. The `evalnoise` CLI analyzes saved per-item results.
