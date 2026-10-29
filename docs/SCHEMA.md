# Input and output schema

UTF-8 JSONL, one object per line. Blank lines are ignored. Scores must be boolean or numeric 0/1. Fractional, missing, and error outcomes are rejected; classify errors explicitly rather than silently dropping them. A scorer failure should stop a run; a genuinely incorrect or malformed model answer is a failed prediction.

Use either one row per sample:

```json
{"model":"A","item_id":"example-1","sample_id":0,"passed":true,"benchmark":"bfcl-subset","condition":"sampling"}
```

or one row per model and item:

```json
{"model":"A","item_id":"example-1","successes":[true,false,true]}
```

Identifiers for models/items are nonempty strings. Sample identifiers are strings or integers and must be unique within a model/item. Do not mix row shapes for a model/item. All models need identical item sets. Items have equal weight even when sample counts differ. `pass@k` requires at least k samples for every model/item. Model generations are assumed conditionally iid and independent across models; matching numeric seeds does not establish common random numbers.

`--model-key`, `--item-key`, `--score-key`, and `--sample-key` accept dotted field paths for sample-row adapters, for example `--score-key grading.passed`. Arbitrary upstream formats need an explicit conversion to this binary schema; the CLI does not guess correctness from generated text. The aggregate array key is `successes`. Unknown fields are preserved in the original input, not copied into the report.

`benchmark` and `condition` may be omitted for a single cohort. Mixed values are rejected. Select cohorts with `--benchmark` and `--condition`; do not pool benchmarks or temperatures. If supplied, `prompt_sha256` must agree for a given item. The runner records a pre-template messages hash and the exact rendered-prompt hash separately because tokenizers differ across models.

The greedy command expects `model`, `item_id`, `run_id`, `temperature:0`, and exact decoded `output`. It needs the same set of at least three runs for each item of a model. Optional `passed` gives score disagreement; `batch_size`, `max_num_seqs`, `arm`, and engine metadata document interventions. Analyze baseline and fix arms separately.

JSON report schema version 1 contains provenance (input SHA256 and package versions), configuration, item/sample counts, and metrics. Each pass@k metric has `items` and `sampling` reports, model CIs and competition-rank distributions, and pairwise differences, CIs, strict win fractions, ties, and strict reversals of the observed order. Observed ties have an undefined (`null`) rank-flip frequency. Planning is available for pass@1 paired comparisons, with a finite-repeat variance correction, MDD at the observed design, and an item/sample grid. `null` minimum samples means the estimated item-variance floor prevents reaching the target at fixed N. Degenerate empirical variance is marked unidentified rather than a zero-cost design.
