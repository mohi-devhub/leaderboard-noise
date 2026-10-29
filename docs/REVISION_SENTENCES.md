# Audit wording revisions

Baseline: commit `5e86b8c428d6209963d7f9f8e3eb167a6fd56ace`, reviewed in [AUDIT.md](../AUDIT.md). This record lists every added, removed, or revised sentence in existing publication text and supporting documentation. Headings, diagram labels, author metadata, and generator strings are included. Sentence groups preserve the exact source wording, including TeX macros; a group can contain adjacent sentences when source syntax joins them. Unchanged sentences are omitted where sentence boundaries allow. The two Python files change string wording only, with identical non-string AST structure. This inventory and the generated verification JSON are bookkeeping, rather than additional changes to study claims.

M1 scopes the observed differences to batch settings plus run-to-run variation and reports the saved same-batch example. M2 distinguishes one-item leads from the two-answer net reversal. L1 corrects driver/host disclosures, L2 labels the method diagram's greedy and sampling paths, and L3 documents original relative-link bases without changing snapshots. The supplied affiliation and email replace the independent-researcher block. The release availability text now identifies the approved release.

## DECISIONS.md

### Change 1

Before: no corresponding sentence or label.

After:

````text
## October 29, 2026: apply the release audit
The user authorized wording corrections and publication of `v0.1.0-paper`.
Default output differences are described as batch-setting plus run-to-run variation because saved same-batch timing repeats also vary.
One-item leads are distinguished from the two-answer net reversal.
The author affiliation and email are updated as supplied by the user.
Driver disclosures, the greedy-only method diagram, and historical snapshot navigation are corrected.
Empirical values, tables, quantitative figures, provenance snapshots, and the original verification receipts remain unchanged.
The current combined report receives only the explicitly requested wording corrections.
The sentence record and revision verification identify every editorial change before publication.
````


## README.md

### Change 2

Before:

````text
# leaderboard-noise: 2–5% of greedy answers change with batching
Batch size changed about 2–5% of greedy answers.
For the near-tied Llama3B/Qwen3-4B pair, the observed flip was a one-item margin out of 500, within exploratory paired 95% intervals of roughly ±3 percentage points.
````

After:

````text
# leaderboard-noise: default answers vary across batch settings and runs
Default decoding changed about 2–5% of greedy answers across batch settings.
Same-batch repeats also varied, so this measures batch-setting plus run-to-run variation under default decoding.
Qwen3-4B changed text and correctness on `parallel_multiple_37` between repeated A10 timing runs at the same batch size.
For the near-tied Llama3B/Qwen3-4B pair, each untied lead is one correct answer out of 500; the reversal is a two-answer net swing.
These leads lie within exploratory paired 95% intervals of roughly ±3 percentage points.
````

### Change 3

Before:

````text
Under batch invariance, decoded outputs were identical across A10 and L4 for all four replicated models.
````

After:

````text
Batch invariance removed all observed text changes across batch settings and timing repeats.
Decoded outputs were identical across A10 and L4 for all four replicated models.
````

### Change 4

Before:

````text
.venv/bin/python scripts/write_study_article.py
````

After:

````text
.venv/bin/python scripts/write_study_article.py --manifest /tmp/leaderboard-noise-combined-sources.json
````

### Change 5

Before:

````text
This local command reads saved A10 and L4 summaries and regenerates `blog/STUDY.md`, `results/REPORT.md`, and the source-hash and winner manifest `results/combined-sources.json`.
````

After:

````text
This local command reads saved A10 and L4 summaries and regenerates `blog/STUDY.md`, `results/REPORT.md`, and a source-hash and winner manifest at the specified temporary path.
The original `results/combined-sources.json` remains the record of the pre-audit documents.
````

### Change 6

Before:

````text
This tests batch sensitivity with controlled offline inference submission, not a production HTTP load generator.
````

After:

````text
This measures variation across batch settings and runs with controlled offline inference submission, not a production HTTP load generator.
````

### Change 7

Before:

````text
## Standalone paper and local release candidate
The [LaTeX manuscript](paper/main.tex) builds to [main.pdf](paper/main.pdf), with six main pages and an appendix.
The paper uses only saved results and discloses the one-item rank margin, exploratory intervals, A10-only throughput cost, hardware confounds, and source-attestation limits.
````

After:

````text
## Standalone paper and release
The [LaTeX manuscript](paper/main.tex) builds to [main.pdf](paper/main.pdf), with an appendix.
The paper uses only saved results and discloses same-batch run variation, one-item leads and the two-answer net reversal, exploratory intervals, A10-only throughput cost, hardware confounds, and source-attestation limits.
````

### Change 8

Before:

````text
The local release archive includes both license texts, the BFCL notice, source snapshots, data, paper, and SHA256 checksums.
The intended local tag is `v0.1.0-paper`.
A fresh-session audit and approval are pending; the GitHub release and remote tag have not been published.
````

After:

````text
The [v0.1.0-paper release](https://github.com/mohi-devhub/leaderboard-noise/releases/tag/v0.1.0-paper) includes both license texts, the BFCL notice, source snapshots, data, paper, and SHA256 checksums.
The [audit](AUDIT.md), [sentence-by-sentence revision record](docs/REVISION_SENTENCES.md), and [verification record](paper/revision-verification.json) document the wording corrections.
See the [snapshot navigation guide](provenance/README.md#historical-document-navigation) for original relative-link context.
````


## blog/POST.md

### Change 9

Before:

````text
# Batching changes 2–5% of greedy answers.
One answer can swap the winner.
Changing batch size changed about 2–5% of greedy answers in my small-model study.
For Llama3B and Qwen3-4B, that was enough to swap rank: the lead was one correct answer out of 500, inside exploratory paired 95% intervals of roughly ±3 percentage points.
The flip is real in the recorded scores; it does not establish which model is better on new questions.
I tested tool calling: choosing the right function and supplying the right arguments.
Six small models ran on an A10 GPU.
I then repeated the two closest comparisons on L4 GPUs, keeping the same questions, model versions, prompts, and grading rules.
Batch sizes were 1, 8, and 32.
Each table cell names the model with more correct answers.
A tie means both scored the same.
"Invariant" is vLLM's setting that removes dependence on the batch.
````

After:

````text
# Default answers vary across batch settings and runs.
One-item leads reverse.
Default decoding changed about 2–5% of greedy answers across batch settings in my small-model study.
Same-batch repeats also varied, so this measures batch-setting plus run-to-run variation under default decoding.
Qwen3-4B changed text and correctness on `parallel_multiple_37` between A10 timing repeats at the same batch size.
Each untied Llama3B/Qwen3-4B lead is one correct answer out of 500; the reversal is a two-answer net swing.
Those leads sit inside exploratory paired 95% intervals of roughly ±3 percentage points.
I tested tool calling: choosing functions and arguments.
Six small models ran on A10.
I repeated the two closest comparisons on L4, retaining the questions, checkpoints, prompts, and grading.
Greedy batch sizes were 1, 8, and 32.
Each cell names the model with more correct answers.
"Invariant" is vLLM's batch-invariance setting.
````

### Change 10

Before:

````text
The second close pair, Qwen2.5-3B versus Qwen3-1.7B, never swaps order.
````

After:

````text
Qwen2.5-3B versus Qwen3-1.7B never swaps order.
````

### Change 11

Before:

````text
Greedy decoding always picks the token with the highest computed score.
But changing a batch can change floating-point arithmetic.
Near a token tie, a tiny numerical difference can change the chosen word and the rest of the answer.
Changed text does not always change correctness, which is why a few changed answers need not overturn a clear lead.
Batch invariance removed the observed text changes.
For all four models repeated on L4, the invariant outputs were also identical across A10 and L4.
But switching it on can itself change the winner: A10's batch-1 lead moves from Qwen to Llama.
Here, invariance stabilizes outputs; it does not choose the best answer.
That stability costs speed.
Across the A10 configurations, median token throughput was 32–60% lower with invariance, measured with three repetitions per configuration.
````

After:

````text
Greedy decoding picks the token with the highest computed score.
Batch shape can change floating-point arithmetic.
Near a token tie, a tiny difference can change the chosen word and the answer.
Changed text does not always change correctness.
Batch invariance removed all observed text changes across batch settings and timing repeats.
For all four models repeated on L4, invariant outputs were identical across A10 and L4.
Switching it on can itself change the winner: A10's batch-1 lead moves from Qwen to Llama.
Stability does not choose the best answer.
Across A10 configurations, median token throughput was 32–60% lower with invariance, measured with three repetitions per configuration.
````

### Change 12

Before:

````text
The two close pairs need approximately 834 and 1,100 items.
````

After:

````text
The close pairs need approximately 834 and 1,100 items.
````

### Change 13

Before:

````text
If you compare models on your own evals, fix the batch size for every model or enable batch invariance for all of them.
````

After:

````text
For your own evals, use the same batch size for every model and repeat default runs, or enable batch invariance throughout.
A fixed batch size alone did not ensure stable outputs here.
````

### Change 14

Before:

````text
These findings cover a frozen BFCL subset and the recorded setups.
All confidence intervals are exploratory; host settings, drivers, and generation history also differ between GPUs.
I did not repeat throughput measurements on L4, and zero observed invariant changes is not a universal determinism guarantee.
The [full report](https://github.com/mohi-devhub/leaderboard-noise/blob/main/results/REPORT.md) includes every model pair, intervals, timings, and costs.
The reusable `evalnoise` CLI applies the same uncertainty analysis to saved per-item results.
````

After:

````text
These findings cover the frozen BFCL subset and recorded setups.
All intervals are exploratory and unadjusted.
CPU limits and generation history differ; hosts are uncontrolled, while retained driver versions match.
I did not repeat throughput measurements on L4, and zero observed invariant changes is not a universal guarantee.
The [full report](https://github.com/mohi-devhub/leaderboard-noise/blob/main/results/REPORT.md) includes every pair, intervals, timings, and costs.
The `evalnoise` CLI analyzes saved per-item results.
````


## blog/STUDY.md

### Change 15

Before:

````text
# Batching changes 2–5% of greedy answers; a one-item lead can swap ranks
Batch size changed about 2–5% of greedy answers.
For the near-tied Llama3B/Qwen3-4B pair, the observed flip was a one-item margin out of 500, within exploratory paired 95% intervals of roughly ±3 percentage points.
````

After:

````text
# Default answers vary across batch settings and runs; one-item leads reverse
Default decoding changed about 2–5% of greedy answers across batch settings.
Same-batch repeats also varied, so this measures batch-setting plus run-to-run variation under default decoding.
Qwen3-4B changed text and correctness on `parallel_multiple_37` between repeated A10 timing runs at the same batch size.
For the near-tied Llama3B/Qwen3-4B pair, each untied lead is one correct answer out of 500; the reversal is a two-answer net swing.
These leads lie within exploratory paired 95% intervals of roughly ±3 percentage points.
````

### Change 16

Before:

````text
Under batch invariance, decoded outputs were identical across A10 and L4 for all four replicated models.
````

After:

````text
Batch invariance removed all observed text changes across batch settings and timing repeats.
Decoded outputs were identical across A10 and L4 for all four replicated models.
````

### Change 17

Before: no corresponding sentence or label.

After:

````text
Each untied lead is one correct answer out of 500; the batch-1 to batch-32 reversal is a two-answer net swing.
````

### Change 18

Before:

````text
## Batch invariance removes the observed batch dependence
````

After:

````text
## Batch invariance removes all observed changes across settings and repeats
````

### Change 19

Before: no corresponding sentence or label.

After:

````text
Same-batch timing repeats also varied under default decoding, so these counts include batch-setting plus run-to-run variation.
````

### Change 20

Before:

````text
Our research question concerns the final step: do batch-sensitive outputs change the ranking of small models on the same BFCL questions, and does batch invariance remove the flip at a measured throughput cost?
````

After:

````text
Our research question concerns the final step: do output differences across batch settings and runs change small-model rankings on the same BFCL questions, and does batch invariance remove the observed flip at a measured throughput cost?
````

### Change 21

Before:

````text
Hosts, regions, and drivers differ.
````

After:

````text
All retained driver versions are 610.57.04.
Host identities and regions are not uniformly recorded, and host allocations are uncontrolled.
````

### Change 22

Before:

````text
.venv/bin/python scripts/write_study_article.py
````

After:

````text
.venv/bin/python scripts/write_study_article.py --manifest /tmp/leaderboard-noise-combined-sources.json
````

### Change 23

Before:

````text
This command reads saved summaries and writes this article, `results/REPORT.md`, and `results/combined-sources.json`.
````

After:

````text
This command reads saved summaries and writes this article, `results/REPORT.md`, and a source-hash and winner manifest at the specified temporary path.
The original `results/combined-sources.json` remains the record of the pre-audit documents.
````


## paper/README.md

### Change 24

Before:

````text
The intended local release-candidate tag is `v0.1.0-paper`.
The archive, local tag, and manuscript await a fresh-session audit and approval.
No public GitHub release or remote tag is published by the build or release packager.
````

After:

````text
The [v0.1.0-paper release](https://github.com/mohi-devhub/leaderboard-noise/releases/tag/v0.1.0-paper) contains the manuscript and reproducibility archive.
The [pre-release audit](../AUDIT.md), [wording revision record](../docs/REVISION_SENTENCES.md), and [revision verification](revision-verification.json) document the corrections.
The original `verification.json` and `results/combined-sources.json` preserve the pre-audit candidate record, including its original document digests.
Only the current combined report has a wording-only change among the original frozen-manifest paths; all empirical artifacts remain unchanged.
Build and packaging scripts do not publish releases.
````


## paper/main.tex

### Change 25

Before:

````text
\title{Leaderboard Noise: Batch-Sensitive Greedy Answers,\\One-Item Rank Flips, and Their Mitigation}
\author{Mohith (\texttt{mohi-devhub})\\\small Independent researcher}
\date{October 2026\quad Local release candidate \texttt{v0.1.0-paper}}
````

After:

````text
\title{Leaderboard Noise: Greedy Variation Across Batches and Runs,\\One-Item Leads, and Their Mitigation}
\author{Mohith\\\small Chinmaya Vishwa Vidyapeeth, Kerala, India\\\small \texttt{achumohith14@gmail.com}}
\date{October 2026}
````

### Change 26

Before:

````text
Changing request batch size changed about \TextRounded{} of greedy decoded answers in a small-model tool-calling study.
For Llama-3.2-3B and Qwen3-4B, a one-correct-answer margin out of \NItems{} items was enough to swap the observed rank.
This is a \OneItemGap{}-percentage-point margin inside exploratory paired intervals of roughly $\pm\PairedHalfWidth{}$ points, with endpoints reaching $\pm\PairedEndpoint{}$; it does not establish population superiority.
````

After:

````text
Default decoding changed about \TextRounded{} of greedy answers across batch settings.
Same-batch repeats also varied, so this measures batch-setting plus run-to-run variation under default decoding.
For Llama-3.2-3B and Qwen3-4B, each untied lead is one correct answer out of \NItems{} items; the reversal is a two-answer net swing.
Each lead is a \OneItemGap{}-percentage-point margin inside exploratory paired intervals of roughly $\pm\PairedHalfWidth{}$ points, with endpoints reaching $\pm\PairedEndpoint{}$; it does not establish population superiority.
````

### Change 27

Before:

````text
Batch-invariant decoding removed all observed batch-induced text changes and produced identical decoded outputs across GPU tiers for every replicated model.
````

After:

````text
Batch-invariant decoding removed all observed text changes across batch settings and timing repeats and produced identical decoded outputs across GPU tiers for every replicated model.
````

### Change 28

Before:

````text
In this study, changing only the controlled greedy request batch setting changes about \TextRounded{} of decoded answers while checkpoint, question, prompt, and request seed stay fixed.
````

After:

````text
Default decoding changed about \TextRounded{} of answers across batch settings while checkpoint, question, prompt, and request seed stayed fixed.
Same-batch repeats also varied, so this measures batch-setting plus run-to-run variation under default decoding.
````

### Change 29

Before:

````text
The interesting case is a near tie: the observed Llama/Qwen rank flip has a one-item margin on \NItems{} questions, within exploratory paired intervals of approximately $\pm\PairedHalfWidth{}$ percentage points.
````

After:

````text
For the near-tied Llama/Qwen pair, each untied lead is one answer out of \NItems{} questions; the reversal is a two-answer net swing.
Each lead lies within exploratory paired intervals of approximately $\pm\PairedHalfWidth{}$ percentage points.
````

### Change 30

Before:

````text
First, default greedy text changes reach \TextExact{} across the recorded models and GPU tiers.
````

After:

````text
First, default greedy text differences reach \TextExact{} across batch settings in the recorded models and GPU tiers.
Same-batch timing repeats also varied, so these differences combine batch-setting and run-to-run variation.
````

### Change 31

Before:

````text
Third, the documented batch-invariance setting removes the observed batch dependence and gives identical cross-tier text for all replicated models, but with a measured A10 throughput penalty.
````

After:

````text
Third, the documented batch-invariance setting removes all observed changes across batch settings and timing repeats and gives identical cross-tier text for all replicated models, but with a measured A10 throughput penalty.
````

### Change 32

Before:

````text
Default and batch-invariant arms each use request batches 1, 8, and 32.
Sampling is collected only on A10.
````

After:

````text
Greedy decoding uses default and batch-invariant arms at request batches 1, 8, and 32.
Sampling uses only the A10 default arm, with request batches of 16 and ten completions per item.
````

### Change 33

Before: no corresponding sentence or label.

After:

````text
In the saved A10 timing repeats, Qwen3-4B changes decoded text and correctness on \code{parallel\_multiple\_37} at the same batch size.
The primary greedy conditions run once each in a fixed order, so the study does not isolate a pure batch-size effect.
````

### Change 34

Before: no corresponding sentence or label.

After:

````text
Each untied lead is one correct answer out of \NItems{}; the batch-1 to batch-32 reversal is a two-answer net swing.
````

### Change 35

Before: no corresponding sentence or label.

After:

````text
Same-batch timing repeats also varied, so these counts measure batch-setting plus run-to-run variation under default decoding.
````

### Change 36

Before:

````text
No invariant process has an observed within-tier batch-induced text or correctness change.
````

After:

````text
Invariant decoding has no observed text or correctness changes across the tested batch settings and timing repeats.
````

### Change 37

Before:

````text
The decisive observed margins are one item, while paired uncertainty is approximately $\pm\PairedHalfWidth{}$ points.
````

After:

````text
Each decisive observed lead is one item and its reversal is a two-answer net swing, while paired uncertainty is approximately $\pm\PairedHalfWidth{}$ points.
````

### Change 38

Before:

````text
Batching changed about \TextRounded{} of greedy decoded answers in this study.
For one near-tied pair, one changed correct answer was enough to alter the observed winner, with the default ordering reversed between recorded A10 and L4 setups.
````

After:

````text
Default decoding changed about \TextRounded{} of greedy answers across batch settings.
Same-batch repeats also varied, so this measures batch-setting plus run-to-run variation under default decoding.
Each untied lead for the near-tied pair is one correct answer out of \NItems{}; the reversal is a two-answer net swing.
The default ordering reverses between the recorded A10 and L4 setups.
````

### Change 39

Before:

````text
Batch invariance removed the observed changes and matched outputs across tiers, at an A10 throughput cost, while sometimes changing the winner itself.
A useful evaluation report should therefore fix or disclose batch policy, retain per-item outcomes, show paired uncertainty, and distinguish stable text from a separated score difference.
````

After:

````text
Batch invariance removed all observed changes across batch settings and timing repeats and matched outputs across tiers, at an A10 throughput cost, while sometimes changing the winner itself.
A useful evaluation report should therefore fix or disclose batch policy, repeat default runs, retain per-item outcomes, show paired uncertainty, and distinguish stable text from a separated score difference.
````

### Change 40

Before:

````text
This paper and reproducibility archive target local release-candidate tag \code{v0.1.0-paper}; publication of the GitHub release and tag is pending approval.
````

After:

````text
The paper and reproducibility archive are available in release \code{v0.1.0-paper} at \url{https://github.com/mohi-devhub/leaderboard-noise/releases/tag/v0.1.0-paper}.
````

### Change 41

Before:

````text
The local tag and archive are prepared for a fresh-session audit.
No public GitHub release is created by the build or packaging scripts.
````

After:

````text
The pre-release audit is retained in \code{AUDIT.md}, and its wording corrections are listed in \code{docs/REVISION\_SENTENCES.md}.
Build and packaging scripts do not publish releases; publication follows verification.
````


## paper/overview.tex

### Change 42

Before:

````text
\node[box,text width=26mm,right=of items] (a10) {A10: \NAtenModels{} models\\sampling + greedy};
\node[box,text width=30mm,right=of a10] (arms) {Default / invariant\\batches 1, 8, 32};
````

After:

````text
\node[box,text width=26mm,right=of items] (a10) {A10: \NAtenModels{} models\\sampling (default) + greedy};
\node[box,text width=30mm,right=of a10] (arms) {Greedy: default / invariant\\batches 1, 8, 32};
````

### Change 43

Before:

````text
\node[box,text width=49mm,below=6mm of a10.south,anchor=north west,xshift=-14mm] (l4) {L4: two close pairs (\NLfourModels{} models)\\greedy only; same items and settings};
````

After:

````text
\node[box,text width=49mm,below=6mm of a10.south,anchor=north west,xshift=-14mm] (l4) {L4: two close pairs (\NLfourModels{} models)\\greedy only; same items and greedy settings};
````


## provenance/README.md

### Change 44

Before: no corresponding sentence or label.

After:

````text
## Historical document navigation
Historical Markdown copies retain their original bytes and relative links.
Open those links relative to the original location below, rather than the nested snapshot directory.
The linked current documents provide working navigation; the snapshots remain evidence of what existed before execution or recovery.
| Historical copy | Original location | Current document |
|---|---|---|
| `results/l4-followup-20261028T190732Z/BUDGET-before-preemption.md` | repository root `BUDGET.md` | [Budget](../BUDGET.md) |
| `results/l4-followup-20261028T190732Z/source-before/BUDGET-A10.md` | repository root `BUDGET.md` | [Budget](../BUDGET.md) |
| `results/l4-followup-20261028T190732Z/source-before/README.md` | repository root `README.md` | [README](../README.md) |
| `results/l4-followup-20261028T190732Z/source-before/STUDY.md` | `blog/STUDY.md` | [Study](../blog/STUDY.md) |
| `results/metadata/BUDGET-before-final.md` | repository root `BUDGET.md` | [Budget](../BUDGET.md) |
For example, resolve a snapshot's `results/study-20261028T065939Z/receipt.json` from the repository root.
Resolve `../results/...` in the copied study from `blog/`.
Historical approval statements and document digests describe their original dates.
The current paper, article, report, and release documentation contain the audit corrections; the archived copies do not receive editorial updates.
````


## results/REPORT.md

### Change 45

Before:

````text
# Batching changes 2–5% of greedy answers: combined A10/L4 report
Batch size changed about 2–5% of greedy answers.
For the near-tied Llama3B/Qwen3-4B pair, the observed flip was a one-item margin out of 500, within exploratory paired 95% intervals of roughly ±3 percentage points.
````

After:

````text
# Default answers vary across batch settings and runs: combined A10/L4 report
Default decoding changed about 2–5% of greedy answers across batch settings.
Same-batch repeats also varied, so this measures batch-setting plus run-to-run variation under default decoding.
Qwen3-4B changed text and correctness on `parallel_multiple_37` between repeated A10 timing runs at the same batch size.
For the near-tied Llama3B/Qwen3-4B pair, each untied lead is one correct answer out of 500; the reversal is a two-answer net swing.
These leads lie within exploratory paired 95% intervals of roughly ±3 percentage points.
````

### Change 46

Before:

````text
Under batch invariance, decoded outputs were identical across A10 and L4 for all four replicated models.
````

After:

````text
Batch invariance removed all observed text changes across batch settings and timing repeats.
Decoded outputs were identical across A10 and L4 for all four replicated models.
````

### Change 47

Before: no corresponding sentence or label.

After:

````text
Each untied lead is one correct answer out of 500; the batch-1 to batch-32 reversal is a two-answer net swing.
````

### Change 48

Before:

````text
## Batch invariance removes the observed batch dependence
````

After:

````text
## Batch invariance removes all observed changes across settings and repeats
````

### Change 49

Before: no corresponding sentence or label.

After:

````text
Same-batch timing repeats also varied under default decoding, so these counts include batch-setting plus run-to-run variation.
````

### Change 50

Before:

````text
GPU family is not causally isolated: generation history, CPU caps, host, and driver also differ.
````

After:

````text
GPU family is not causally isolated: generation history and CPU caps differ, and host allocations are uncontrolled.
All retained driver versions are 610.57.04; host identities are not uniformly recorded.
````


## scripts/package_release.py

### Change 51

Before:

````text
local release candidate; no remote publication by this script
````

After:

````text
release tag; publication managed separately from packaging
````

### Change 52

Before:

````text
pending
````

After:

````text
completed; see AUDIT.md and paper/revision-verification.json
````


## scripts/write_study_article.py

### Change 53

Before:

````text
Batch size changed about 2–5% of greedy answers. For the near-tied Llama3B/Qwen3-4B pair, the observed flip was a one-item margin out of 500, within exploratory paired 95% intervals of roughly ±3 percentage points. The separate sampling analysis projects roughly 800–1,100 items to resolve a 3-point gap, with ten sampled answers per item per model.
Under batch invariance, decoded outputs were identical across A10 and L4 for all four replicated models. Switching to invariance can itself change the winner: at A10 batch 1, the lead moves from Qwen3-4B to Llama3B. Median token throughput was 32–60% lower in the repeated A10 timing study.
````

After:

````text
Default decoding changed about 2–5% of greedy answers across batch settings. Same-batch repeats also varied, so this measures batch-setting plus run-to-run variation under default decoding. Qwen3-4B changed text and correctness on `parallel_multiple_37` between repeated A10 timing runs at the same batch size. For the near-tied Llama3B/Qwen3-4B pair, each untied lead is one correct answer out of 500; the reversal is a two-answer net swing. These leads lie within exploratory paired 95% intervals of roughly ±3 percentage points. The separate sampling analysis projects roughly 800–1,100 items to resolve a 3-point gap, with ten sampled answers per item per model.
Batch invariance removed all observed text changes across batch settings and timing repeats. Decoded outputs were identical across A10 and L4 for all four replicated models. Switching to invariance can itself change the winner: at A10 batch 1, the lead moves from Qwen3-4B to Llama3B. Median token throughput was 32–60% lower in the repeated A10 timing study.
````

### Change 54

Before:

````text
Batch invariance removes the observed batch dependence
````

After:

````text
Batch invariance removes all observed changes across settings and repeats
````

### Change 55

Before:

````text
) explains selection, prompting, seeds, mitigation, and inference controls. GPU family is not causally isolated: generation history, CPU caps, host, and driver also differ. Each comparison has only one recorded card per GPU family. The A10 default process sampled before greedy generation; L4 starts greedy evaluation after smoke and the same warmup protocol. L4 requests and caps two CPU cores; A10 requested two and capped four. Findings do not cover other serving schedules, training seeds, native tool APIs, or executed code.

````

After:

````text
) explains selection, prompting, seeds, mitigation, and inference controls. GPU family is not causally isolated: generation history and CPU caps differ, and host allocations are uncontrolled. All retained driver versions are 610.57.04; host identities are not uniformly recorded. Each comparison has only one recorded card per GPU family. The A10 default process sampled before greedy generation; L4 starts greedy evaluation after smoke and the same warmup protocol. L4 requests and caps two CPU cores; A10 requested two and capped four. Findings do not cover other serving schedules, training seeds, native tool APIs, or executed code.

````

### Change 56

Before:

````text
On A10, Qwen3-4B ranks above Llama3B at batch 1, they tie at batch 8, and Llama3B ranks above Qwen3-4B at batch 32. On L4, Llama3B ranks above Qwen3-4B at batch 1, they tie at batch 8, and Qwen3-4B ranks above Llama3B at batch 32. Thus the strict full-set flip reproduces, but the winner at each untied setting reverses between GPUs.
````

After:

````text
On A10, Qwen3-4B ranks above Llama3B at batch 1, they tie at batch 8, and Llama3B ranks above Qwen3-4B at batch 32. On L4, Llama3B ranks above Qwen3-4B at batch 1, they tie at batch 8, and Qwen3-4B ranks above Llama3B at batch 32. Thus the strict full-set flip reproduces, but the winner at each untied setting reverses between GPUs. Each untied lead is one correct answer out of 500; the batch-1 to batch-32 reversal is a two-answer net swing.
````

### Change 57

Before:

````text
An item changes text if any of its three batch outputs differ. Correctness changes count items whose official BFCL pass/fail result differs. Wilson intervals below are exploratory under an independent-item approximation. Questions recur across models and GPUs, so these observations must not be pooled as independent questions.
````

After:

````text
An item changes text if any of its three batch outputs differ. Same-batch timing repeats also varied under default decoding, so these counts include batch-setting plus run-to-run variation. Correctness changes count items whose official BFCL pass/fail result differs. Wilson intervals below are exploratory under an independent-item approximation. Questions recur across models and GPUs, so these observations must not be pooled as independent questions.
````

### Change 58

Before:

````text
# Batching changes 2–5% of greedy answers: combined A10/L4 report


````

After:

````text
# Default answers vary across batch settings and runs: combined A10/L4 report


````

