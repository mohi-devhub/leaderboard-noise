# Estimands and experiment

The primary metric is expected pass@1 for a single call to a frozen checkpoint under a fixed decoding configuration. For each item i and model A, estimate p(A,i) by averaging binary outcomes across n independent generations. Average those item means with equal item weight.

## Three distinct measurements

1. **Item bootstrap:** sample N item indices with replacement; use exactly the same indices for every model and carry all observed generations for each selected item. Recompute the metric and paired differences. The 2.5/97.5 percentiles are a 95% percentile interval. This procedure represents uncertainty for repeated item-level observation vectors drawn from an assumed population. Their finite-generation noise is already present. It is not a noise-free estimate of pure between-item variance.
2. **Conditional sampling bootstrap:** keep all items fixed and resample generations independently within each model/item. Binary outcomes make this exactly a binomial draw from the empirical success fraction. It measures generation variability conditional on the observed items and empirical probabilities. Report it separately; do not sum these two bootstrap variances. For k>1, empirical resampling can be biased and is diagnostic, while the original pass@k point estimate is unbiased under iid generation.
3. **Greedy intervention:** same checkpoint, dtype, prompts, token limit, seed, and scorer; vary batch size/concurrency. Measure exact decoded output changes, token-ID changes, pass/fail changes, and rankings separately. This is a controlled configuration-sensitivity test, not an estimate of an uncontrolled production failure rate. A zero-change pilot is an honest null result.

Repeated generations are not independent benchmark items. Related questions can also share templates/functions. The initial analysis assumes independent items; before population claims, inspect that dependence and add a defensible cluster unit or restrict interpretation. Do not silently invent clusters. Multiple pairwise intervals are exploratory and unadjusted; they do not justify a simultaneous “best model” claim.

## Pass@k and comparisons

For c successes among n generations, use `1 - C(n-c,k)/C(n,k)` and require n>=k. Primary pass@1, secondary pass@5/pass@10. Pass@k presumes an oracle that can recognize a correct candidate; it is not majority voting. State exact n, including truncations (scored with the same checker) and infrastructure failures (must be repaired or reported as incomplete).

`P(A beats B)` means the fraction of bootstrap draws with score A strictly greater than B. Ties get their own mass. It is neither a Bayesian posterior nor a null-hypothesis p-value. A rank flip is a strict reversal relative to the observed point-score order; an observed tie has no direction to reverse. Competition ranks give all tied leaders rank 1.

## Approximate planning, not a guarantee

Let d_i be the difference of observed item means, s²_d their sample variance, and v_iA/v_iB the within-item unbiased outcome variances. Assuming independent generations across models, estimate the finite-repeat term `q = mean(v_iA/n_iA + v_iB/n_iB)`. Estimate pure paired item variance `tau² = max(0, s²_d-q)` and report when clipping was necessary. Let `omega² = mean(v_iA+v_iB)`.

For a proposed balanced design with N items and m samples per model/item, approximate `Var(delta_hat) = (tau² + omega²/m)/N`. For two-sided alpha and power 1-beta, use `z = Phi^-1(1-alpha/2)+Phi^-1(1-beta)` and `MDD = z*sqrt(Var)`. Required N is the ceiling of `z²*(tau²+omega²/m)/gap²`. Solve the same expression for minimum integer m at fixed N; report unattainable when the item-variance floor is too high. Default alpha=.05, power=.8, gap=.05 are design choices, not measurements.

Small pilots can poorly estimate rare failures and variance floors. Boundary samples cannot prove zero uncertainty. These projections apply to pass@1 and the same item distribution, not guaranteed discovery, post-selection power, or pass@10. Validate allocations with the pilot before the full run.

## Frozen pilot and mitigation

Pilot: Qwen2.5-0.5B/1.5B-Instruct, 100 identical items, temperature=.7, n=10 using vLLM's n parameter, plus three greedy configurations per model and arm. Primary subset: 500 frozen items from Python single-turn simple/multiple/parallel/parallel_multiple BFCL categories, sampled proportionally 200/100/100/100; pilot uses a nested 40/20/20/20 subset. Seed 20261101 is a predeclared arbitrary seed, not the run date.

Use explicit per-request SamplingParams, never a single seeded object broadcast to every prompt. Allocate seed blocks as `root + fixed_model_index*1000000 + fixed_full_subset_item_index*100`, with n<=100. This gives nonoverlapping child seeds across the declared model/item roster while remaining independent of request ordering and batch size. Distinct PRNG streams support the sampling design; they do not guarantee hardware reproducibility. Greedy comparisons keep each item's seed unchanged across arms/configurations.

Use official BFCL prompting-mode instructions and official AST decoder/checker. This standardizes the task across small models; it does not measure each model's best native tool API. Freeze candidate IDs, source file hashes, model revisions, prompt construction, token limits and scorer version before generation. No score-driven item selection. The model list is a candidate roster; ability proximity is not assumed from parameter count.

Mitigation: `VLLM_BATCH_INVARIANT=0` versus `1`, set before importing vLLM. The setting exists in v0.32.0; hardware/model compatibility still needs a runtime check. Compare throughput at each matched configuration using identical prompts. Separate startup/download/warmup time from measured decode time; report completions/s and generated tokens/s, token counts and truncation fractions. Startup costs remain part of budget accounting. A full study should counterbalance arm order and repeat timing; a pilot timing ratio alone is descriptive.

## Completed six-model protocol

The subsequent [frozen full-study plan](FULL_STUDY_PLAN.md) uses six selected checkpoints and all 500 items. It adds three matched 100-item timing repetitions per arm and batch size, with alternating arm order in fresh processes. Primary accuracy uses 48,000 predictions; 10,800 separate timing outputs never increase its sample count. The full study completed on A10, with the preserved first model on an earlier device and the remaining five on one shared second device. Both observed-close pairs share that second GPU. Every model's arms stay on its assigned device.

For greedy batch flips, jointly resample item vectors across both models and all three batch settings. Count opposite strict orders across settings in the same draw; exclude ties. Use 5,000 resamples for the point fraction. An outer paired-item bootstrap with 500 outer and 1,000 inner draws gives exploratory percentile intervals. This discontinuous statistic can produce collapsed, poorly calibrated intervals at boundaries or with missing empirical patterns. Separate Wilson intervals quantify only finite Monte Carlo precision conditional on the observed dataset. Report paired score-difference intervals and observed full-set flips alongside these fractions.

The full report also distinguishes a within-arm batch flip from changing the winner when enabling the mitigation at a fixed batch size. Text changes use Wilson intervals under an independent-item approximation. Published-score preselection and additional observed-close labels remain separate. See the [complete numerical report](../results/REPORT.md), including all 15 pairs, null results, limitations, and the tokenization correction made before Llama started.
