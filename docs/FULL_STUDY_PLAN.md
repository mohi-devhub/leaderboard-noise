# Six-model A10 study plan

Frozen before full-study inference, October 28, 2026. The user approved choosing a new roster to target close comparisons. Selection uses pilot results and published BFCL scores, never observed ranking flips.

## Selection rationale

The pilot's Qwen0.5B/1.5B gap was 32 points, so Qwen0.5B is excluded. Qwen2.5-1.5B remains the measured anchor, and Qwen2.5-3B adds its next size. Three other models form a close published single-turn cluster. Qwen3-4B-Instruct-2507 adds a somewhat stronger small-model comparison.

| Checkpoint | Selection evidence | License |
|---|---|---|
| Qwen2.5-1.5B-Instruct | Pilot sampling pass@1 83.9%; default greedy 85% | Apache 2.0 |
| Qwen2.5-3B-Instruct | Next size above the pilot anchor; no matching published BFCL number found | Qwen Research License |
| Qwen3-1.7B, non-thinking | Published non-live AST 82.92% | Apache 2.0 |
| Llama-3.2-3B-Instruct | Published non-live AST 82.67% | Llama 3.2 Community License and AUP |
| xLAM-2-3b-fc-r | Published non-live AST 82.96% | CC BY-NC 4.0 research release |
| Qwen3-4B-Instruct-2507 | Published non-live AST 86.44% in prompting mode | Apache 2.0 |

Source: [official BFCL leaderboard](https://gorilla.cs.berkeley.edu/leaderboard.html) and its [CSV](https://gorilla.cs.berkeley.edu/data_overall.csv), retrieved October 28. The three cluster scores come from FC rows. This experiment uses identical official prompting-mode instructions and AST decoding for every model. Published scores also include other languages and weighting. They guide selection but cannot guarantee three close pairs on our 500-item subset.

Preselected pairs are Qwen3-1.7B versus Llama3.2-3B, Qwen3-1.7B versus xLAM3B, and Llama3.2-3B versus xLAM3B. Published gaps are 0.25, 0.04, and 0.29 points. Report all 15 pairs, identify every observed default-serial gap at most three points, and retain preselected pairs even if they are not close here. Never change checkpoints or items after seeing full-study outcomes to force a flip.

`experiments/full-models.json` freezes revisions and seed indices. Official license/configuration files and hashes are in `results/metadata/full-model-sources.json`. Llama's gated config download succeeded using the existing credential. Pass the credential as an ephemeral Modal secret, never in payloads or artifacts. Evaluate research/noncommercial checkpoints without redistributing weights. Preserve the original manifest and pilot.

Qwen3-1.7B uses its [documented `enable_thinking=False` switch](https://huggingface.co/Qwen/Qwen3-1.7B). The 2507 model supports non-thinking only. Common temperature, top-p, and output limits control comparisons; they do not optimize each model's leaderboard score.

## Workload and repeated timing

Use all 500 frozen BFCL Python single-turn items. Each model produces ten samples/item at temperature 0.7 in the default arm, then greedy outputs at request batch sizes 1, 8, and 32 in both arms. Primary evaluation totals 48,000 predictions. A10, vLLM 0.32.0, bfloat16, eager execution, engine concurrency 64, and disabled prefix cache are shared.

Throughput uses the same nested 100-item pilot set in three additional repetitions per arm and batch configuration. All repetitions perform identical work. Fresh model processes alternate default/invariant, invariant/default, default/invariant across repetitions. The first two processes also produce the 500-item evaluation before timing. Warmup is outside the timer, while initialization, downloads, smoke, and warmup remain part of cost. Timing adds 10,800 scored predictions, giving 58,800 total. Distinct timing conditions never count as extra independent accuracy samples.

Report every timing, median, range, tokens/s, completions/s, and fix/default ratios. Three repetitions describe this configuration; they do not establish general production performance or an adoption recommendation. Record host load, GPU driver, CUDA, packages, prompt hashes, token IDs, format errors, and truncations. This is offline inference, not an HTTP load test.

## Flip uncertainty

Stochastic uncertainty uses paired item bootstrap and unbiased pass@k. Strict rank reversals exclude ties. For greedy sensitivity, resample items jointly across models and batch settings, then measure whether configurations produce opposite strict pairwise rankings. Report both arms, actual orders at each batch size, and paired score-difference intervals.

Use an outer paired item bootstrap around the inner flip-frequency calculation for exploratory percentile intervals. This discontinuous stability functional can behave poorly at ties and boundaries. Report Monte Carlo precision separately. Zero observed flips cannot establish impossibility. Give text-change rates Wilson intervals under an independent-item approximation, and state limitations from shared functions/templates and multiple comparisons.

Also report whether enabling the mitigation changes the observed pairwise winner at a fixed batch size. This is a separate comparison from batching sensitivity within an arm. A mitigation can stabilize its own outputs while selecting a different stable accuracy and order.

## Budget and lifecycle

The [forecast](../experiments/full-forecast.json) scales measured Qwen1.5B A10 pilot times by workload and explicit model factors. Expected study spend is $7.3310. Conservative sequential allowances total $9.8744. Prior estimated spend is $0.3035, so the conservative project forecast is $10.1780 against $12. Each model is a separate batch with a $1.14–$2.16 allowance, below the $5 approval threshold.

Before each model, compare cumulative resource estimates plus the next bounded allowance with $12. Stop if the next would cross it. Enforce execution deadlines through subprocess timeouts and an independent process watchdog. A10 is the only GPU; stop after 30 minutes without allocation. Never resubmit an uncertain job. Permit one connection reattachment to its saved call ID.

Account-wide billing changes include parallel qunti-check usage and cannot be called study costs. Keep tagged usage, resource estimates, reservations, and invoice actuals distinct. Stop only this study's app and verify its containers are gone. Preserve unrelated apps. Finish before October 31 IST. Optional code execution is outside this BFCL launch.

The first full-study allocation returned `NVIDIA A10G` for `gpu="A10"` and an overly strict guard stopped before inference. [Modal's pricing documentation](https://modal.com/pricing) explicitly uses A10G for this tier. The corrected guard accepts the two reported A10-tier names and requires one exact GPU UUID throughout the full study. It does not pool results with the earlier pilot's device. The failed setup adds a conservative $0.02 estimate, so the refreshed conservative project forecast is $10.1980.

## Approved recovery after infrastructure interruption

The preceding budget and one-device plan describe the original launch. That app stopped after Qwen2.5-1.5B completed. Its outputs are retained. The user subsequently approved one detached remaining-five job with a $6.52 forecast, the same $12 project cap, and per-model volume checkpoints. The five new models share one A10; the preserved anchor used an earlier A10. All three preselected close comparisons are among the five new models and therefore share a physical GPU. Cross-device anchor comparisons remain labeled in the results.

The continuation uses a server-side CPU controller and one GPU call for all five models. Local disconnection does not stop that call. Before each model, the controller checks cumulative resource estimates and the next bounded allowance. It commits each completed model and a SHA256 manifest to the volume. Local download verifies hashes before deleting the temporary volume. The original model, item, scoring, sampling, and timing plan remains fixed.

Before the Llama process started, a CPU tokenization check found that the rendered chat already includes Llama's beginning-of-sequence token. The worker now sets `add_special_tokens=False` for that model's rendered prompts. No Llama output preceded the correction. Other models' token IDs were unchanged across all 500 prompts. Source snapshots and the installation receipt document this correction in the running container; no model or item was replaced.
