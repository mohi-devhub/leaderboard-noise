# Pre-release audit: leaderboard-noise

Audited October 29, 2026. Target: local tag `v0.1.0-paper`, commit `5e86b8c428d6209963d7f9f8e3eb167a6fd56ace`, and its compiled [paper/main.pdf](paper/main.pdf).

**Verdict: revise two interpretation/wording points before release.** The reported numerical tables and quantitative figures agree with the frozen artifacts. All 11 citations exist and support their stated related-work claims. The novelty statement is appropriately limited. I found two medium-severity issues and three low-severity presentation/documentation issues below; no critical or high-severity numerical, citation, or packaging defect was found.

This review independently read the PDF, source, original model JSON, scored per-item rows, analysis implementation, primary literature, and archive contents. Author-supplied verification receipts were cross-checked rather than accepted as proof. Only this audit document was added. No manuscript, frozen result, tag, or archive was changed; no model inference, BFCL rescoring, study bootstrap rerun, remote compute, or publication was performed.

## Findings, ranked by severity

### 1. Medium — The wording attributes more exclusively to batch size than the design establishes

**Location:** introduction, PDF p. 1, [main.tex line 30](paper/main.tex#L30); descriptions of “batch-induced” changes in the abstract and results.

The 2.0–4.6% statistic correctly counts questions with different outputs across the three recorded batch configurations. However, the primary greedy conditions run once each in a fixed sequence. This does not separate a pure batch-size effect from execution history or other run variability. The paper discloses generation-history differences between GPU tiers, but not this limitation of attribution within a tier.

The frozen timing data supply a concrete counterexample to interpreting nominal batch size as the only relevant source of variation. In [the A10 Qwen3-4B model artifact](results/study-20261028T065939Z/Qwen3-4B-Instruct-2507.json), default timing repetitions 1 and 2 for `parallel_multiple_37`, at **the same batch size 32**, use the same checkpoint, prompt digest, request seed `35302801`, worker-source digest, and physical GPU. Their decoded calls nevertheless differ: the `get_important_figures` argument changes from `number=5` to `number=1`. The corresponding [scored rows](results/study-20261028T065939Z/scored.jsonl) change from incorrect to correct. The same example also varies at batch 8. Both repetitions are fresh, timing-only processes; this is not merely comparing the primary evaluation with timing.

This does **not** invalidate the saved winner sequences, the text-change counts, or the observed mitigation result. It means the 2–5% should be described as differences **across the recorded batch configurations**, rather than an isolated causal effect of batch size alone. Recommend adding the same-batch timing observation and explicitly stating that the full 500-item greedy conditions were not repeated/counterbalanced to isolate that effect. This clarification can use existing artifacts; no new compute is needed.

### 2. Medium — The conclusion confuses a one-item lead with one changed answer

**Location:** conclusion, PDF p. 6, [main.tex line 168](paper/main.tex#L168): “one changed correct answer was enough to alter the observed winner.”

A **one-item margin** is supported. A strict rank reversal caused by just **one changed correct answer** is not what the retained batch-1 to batch-32 comparison shows:

| GPU, default arm | Llama correct, batch 1 → 32 | Qwen correct, batch 1 → 32 | Llama-minus-Qwen gap |
|---|---:|---:|---:|
| A10 | 457 → 457 | 458 → 456 | −1 → +1 |
| L4 | 458 → 458 | 457 → 459 | +1 → −1 |

On A10, Qwen changes correctness on four items between those endpoints: three losses and one gain, a net loss of two. Llama changes correctness on none. On L4, Qwen has three gains and one loss; Llama has one gain and one loss. The net relative-score swing is again two answers. Moving a one-item lead to the opposite strict one-item lead requires that two-count swing; a single one-sided correctness change would produce a tie.

Evidence: the two sessions’ `scored.jsonl` files and the [combined winner table](results/REPORT.md#which-model-ranks-higher-at-each-default-batch-size). Recommend replacing the conclusion’s sentence with wording about **a one-item lead reversing across batch settings**. The abstract and results already distinguish the endpoint margin correctly.

### 3. Low — The combined report incorrectly says driver versions differ

**Location:** [results/REPORT.md line 270](results/REPORT.md#L270), “generation history, CPU caps, host, and driver also differ.”

All 44 retained process metadata records report driver `610.57.04`. The paper’s limitations and Table 7 correctly state this. The report therefore contradicts both the manuscript and its own underlying metadata. Host identities are not uniformly recorded either, so host allocation should be described as uncontrolled rather than a fully measured causal difference.

Recommend aligning the report’s confound description with the paper. The conclusion that GPU architecture is not causally isolated remains correct because CPU limits, allocations, generation history, and physical cards were not controlled in a randomized crossover.

### 4. Low — Figure 1 visually applies the greedy batch settings to sampling

**Location:** PDF p. 3, [overview.tex lines 3–8](paper/overview.tex#L3).

The arrow from “A10: 6 models / sampling + greedy” enters a shared “Default / invariant / batches 1, 8, 32” box. Read on its own, this suggests sampling used both arms and those batch sizes. In fact, sampling was **default only**, with request batches of **16**, temperature 0.7, and `n=10`. Both arms and batches 1/8/32 apply to greedy evaluation. Section 3.2, Appendix A, configuration, and worker source describe the actual procedure correctly.

Recommend labeling that box “greedy” and annotating the separate default-only sampling path or caption. The model/item counts and L4 selection timing in the diagram are correct.

### 5. Low — Historical Markdown snapshots retain broken relative navigation

The PDF’s 12 unique external URLs resolve, and the current README, report, article, and notices have working local file destinations. A broader scan of tracked Markdown found **54 unresolved relative-link occurrences among 151 checked**, all confined to five historical copies:

| Historical file | Unresolved occurrences |
|---|---:|
| `results/l4-followup-20261028T190732Z/BUDGET-before-preemption.md` | 8 |
| `results/l4-followup-20261028T190732Z/source-before/BUDGET-A10.md` | 8 |
| `results/l4-followup-20261028T190732Z/source-before/README.md` | 16 |
| `results/l4-followup-20261028T190732Z/source-before/STUDY.md` | 17 |
| `results/metadata/BUDGET-before-final.md` | 5 |

For example, a copied root README still links to `blog/STUDY.md` relative to its new nested snapshot directory. These are navigation failures caused by preserving original bytes, not missing scientific results. Recommend explaining original path context in a current release index or provenance guide. **Do not rewrite the frozen snapshots to repair their links.** This finding does not affect the paper’s availability URL or bibliography.

## Numerical and figure verification

The original model-job rows and scored rows preserve identical output strings, token IDs, prompt hashes, and other generation fields. I checked row uniqueness and complete item coverage, directly counted correctness and text changes, calculated Wilson intervals and unbiased pass@k point estimates independently, and calculated the two MDD/item projections independently from paired per-item sample means. Saved bootstrap endpoints were checked against the paper and report; their simulation was not rerun. The resampling implementation preserves joint item patterns across both models and batch settings and excludes ties from strict flips.

| Paper artifact | Audit result |
|---|---|
| Table 1: winners | All four GPU × arm rows match direct correctness counts, including ties. |
| Table 2: changes | All ten model × GPU rows match direct string/pass-fail comparisons. Wilson endpoints match independent calculation. Invariant text and correctness counts are zero. |
| Table 3: flips | All four estimates and outer intervals match the saved paired-comparison JSON and combined report. Definitions and exploratory labels match the implementation. |
| Table 4: MDD/items | 3.87 pp / 834 items and 4.45 pp / 1,100 items match independent calculations and saved planning artifacts. |
| Table 5: analysis seeds | All eight seeds match the saved GPU/arm/pair analyses; 5,000 main, 500 outer, and 1,000 inner draws match saved settings. |
| Table 6: revisions/licenses | All six checkpoint hashes, seed indices, and license identifiers match the frozen roster and retained model metadata. |
| Table 7: hardware | All ten rows match original UUID prefixes, driver strings, and visible CPU observations. |
| Table 8: paired gaps | All 24 gaps match direct counts; every displayed interval matches the saved JSON and report, including L4 default batch 32’s asymmetric [−3.00, +2.80] interval. |
| Table 9: sampling | All six pass@1/pass@5/pass@10 estimates match direct application of the combinatorial estimator; all displayed pass@1 intervals match saved item-bootstrap endpoints. |
| Figure 1: method | Counts and greedy design match; sampling-path ambiguity is finding 4. |
| Figure 2: rank order | All 24 plotted counts agree with raw results. GPU/arm/model labels and grayscale markers agree. Caption explicitly discloses the 455.5–459.5 zoom; these are counts, not CI bars. |
| Figure 3: throughput | All 18 medians/ranges match 54 paired token-rate ratios recomputed from raw token IDs and original elapsed times. Each timed cell contains 100 outputs; there are three repetitions. A10-only scope and “not confidence intervals” are explicit. |

All 39 numerical macros match saved inputs and their rendered TeX. This includes the six/four model counts; 500 items; ten stochastic samples; 58,800 A10 outputs (48,000 primary plus 10,800 timing); 12,000 L4 outputs; and the 70,800 total. Category counts are 200 simple-Python and 100 each multiple, parallel, and parallel-multiple. Versions, seed formula, temperature, context/token limits, eager mode, disabled prefix cache, engine limit 64, model revisions, Qwen3 non-thinking argument, and Llama BOS handling match configurations, metadata, and shipped worker sources. Timing boundaries include output collection and final CUDA synchronization and exclude warmup/startup as described. The 17 A10 truncations, 913 AST decoder failures, and zero L4 truncations also match scored rows.

The budget ledger sums to **$10.721298334852849**, matching the paper’s rounded **$10.7213** estimate. The L4 forecast **$3.6089**, gross metering **$2.7296**, and conservative estimate **$3.1575** match receipts. They are properly distinguished from unknown settled invoices. Released reservations sum to zero active holds. Cleanup statements have saved receipts; this audit did not query or alter live Modal apps.

### Interpretation checks that pass

- **One-item flip:** the observed endpoint margins are 1/500 = 0.2 pp. The abstract immediately places them inside exploratory paired intervals of approximately ±3 pp, reaching ±3.2 pp. No separated population winner is claimed. Finding 2 concerns only the conclusion’s changed-answer wording.
- **Cross-GPU equality:** direct comparison of raw decoded strings and correctness confirms equality for every replicated model in the invariant arm: four models × 500 items × three batch settings, or 6,000 paired comparisons. These are repeated comparisons on the same questions, not 6,000 independent questions. The claim is correctly limited to retained requests; it is not a guarantee of equal logits, universal hardware invariance, or future reproducibility.
- **Mitigation can change the winner:** verified at A10 batch 1 and L4 batch 32. Invariant Llama is 458/500 and Qwen is 457/500 throughout. Stability is not presented as increased accuracy.
- **Throughput:** independently derived median-ratio extrema are 0.3999802 and 0.6775857, yielding the rounded 32–60% reduction. These are measured A10 configuration costs. The paper explicitly excludes an L4 throughput claim and a universal vLLM performance claim.
- **Planning:** roughly 800–1,100 items is a conditional stochastic pass@1 projection at ten answers per item/model, 5% two-sided significance and 80% power. It is explicitly not a greedy one-answer sample-size guarantee. More samples at 500 items do not meet the target under these saved variance estimates.
- **Intervals/confounds:** intervals are labeled exploratory and unadjusted, including the global appendix disclosure. Collapsed [0,0] intervals are explicitly not guarantees. Shared-template dependence, exploratory A10 pair selection, one physical card per comparison pair/tier, differing CPU caps, unrecorded host identity, and execution history are disclosed. GPU architecture is not claimed to be causally isolated.

## Citation and novelty audit

Every entry in [references.bib](paper/references.bib) was checked against its primary source. No citation was missing, fabricated, or materially misdescribed. In particular, Song is not misrepresented as a batch-invariance experiment, and Gond’s alternative is not claimed as implemented here.

| Citation | Primary-source check and support |
|---|---|
| **Yuan et al. (2025)** | [NeurIPS 38 proceedings](https://proceedings.neurips.cc/paper_files/paper/2025/hash/f80094a824ba5912d4a2de169c404a40-Abstract-Conference.html) confirms title, ten authors, venue, and DOI. The paper directly investigates batch-size/GPU/count numerical variability and LayerCast’s higher-precision computation. The manuscript’s description is accurate. |
| **Gond et al. (2026)** | [arXiv:2601.17768v2](https://arxiv.org/abs/2601.17768v2) confirms Raja Gond, Aditya K Kamath, Ramachandran Ramjee, and Ashish Panwar; title/version/year match. Its fast path plus fixed-shape verifier and rollback supports the stated distinction from making every kernel batch invariant. |
| **Atıl et al. (2025)** | [ACL Anthology, Eval4NLP](https://aclanthology.org/2025.eval4nlp-1.12/) confirms title, authors, pp. 135–148, and DOI. TARr@N measures raw-output agreement and TARa@N parsed-answer agreement in hosted settings. This supports the manuscript’s distinction, not an attribution of all API variation to batching. |
| **Song et al. (2025)** | [ACL Anthology, NAACL](https://aclanthology.org/2025.naacl-long.211/) confirms the four authors, title, pp. 4195–4206, and DOI. Greedy versus sampling, repeated outputs, and best-of-N are its subject; the manuscript describes that scope correctly. |
| Madaan et al. (2024) | [arXiv:2406.10229v1](https://arxiv.org/abs/2406.10229v1) confirms authors/title and supports initialization/checkpoint variation and continuous-versus-discrete measurements. |
| Evan Miller (2024) | [arXiv:2411.00640v1](https://arxiv.org/abs/2411.00640v1) confirms title/author and supports question-population reasoning, paired comparisons, and power/sample-size planning. |
| Sida Wang (2025) | [arXiv:2512.21326v1](https://arxiv.org/abs/2512.21326v1) explicitly separates prediction/data/total noise and introduces all-pairs paired analysis. The manuscript attributes these ideas rather than claiming them. |
| Horace He and Thinking Machines Lab (2025) | [Author publication](https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/) confirms byline, date, preferred citation, and DOI. It supports batch-dependent arithmetic and the distinction between deterministic kernels and batch-invariant inference. |
| vLLM maintainers, version 0.32.0 | [Versioned documentation](https://docs.vllm.ai/en/v0.32.0/features/batch_invariance/) exists and explicitly documents `VLLM_BATCH_INVARIANT=1`, including offline inference. |
| Patil et al. (2025) | [PMLR 267](https://proceedings.mlr.press/v267/patil25a.html) confirms seven authors, title, pp. 48371–48392, and BFCL’s AST evaluation method. The manuscript correctly distinguishes this subset from the official overall leaderboard. |
| Chen et al. (2021) | [arXiv:2107.03374v2](https://arxiv.org/abs/2107.03374v2) confirms title/authors/version. Section 2.1 and Appendix A support the unbiased combinatorial pass@k estimator; the manuscript states its sampling assumptions. |

**Novelty verdict:** accurate as written. Yuan already establishes numerical sensitivity to serving configurations and studies a mitigation; Wang already supplies the noise decomposition, paired analysis, and all-pairs framing. Neither phenomenon nor statistical method is a new contribution here. The manuscript explicitly limits its contribution to a small-model BFCL replication, tracing text changes through official correctness checks into fragile finite-set rankings, measuring an existing mitigation’s A10 cost, accounting for costs, and shipping a CLI/provenance workflow. That is a defensible practical contribution. It does not establish priority for discovering rank instability, a new determinism mechanism, or a new variance theory, and it does not claim those things. Finding 1 concerns causal wording, not novelty.

## Release verification

| Check | Result |
|---|---|
| Target identity | `HEAD` and local `v0.1.0-paper` resolve to the same audited commit. PDF has six main pages plus three appendix pages. All nine pages were visually reviewed; no clipping or unreadable/mislabeled quantitative figure was found. `pdfimages` reports no embedded raster images. |
| Original-code license | Root MIT `LICENSE` exists with the project copyright. |
| BFCL attribution | Apache-2.0 license text matches [official Gorilla LICENSE](https://raw.githubusercontent.com/ShishirPatil/gorilla/main/LICENSE) byte for byte. `third_party/BFCL/NOTICE` credits BFCL, identifies version and usage, and honestly identifies itself as project-supplied attribution. |
| Distribution contents | The research archive, wheel, and source distribution each contain byte-identical MIT license, BFCL license, and BFCL notice. Third-party notices distinguish original-code licensing from benchmark/model terms. |
| Model restrictions | Frozen license evidence and manuscript disclose Qwen2.5-3B research/noncommercial terms, xLAM CC BY-NC 4.0, and Llama community/AUP restrictions. No weights are packaged. This checks disclosure, not a legal certification of every use. |
| Provenance | All 13 snapshots match their source bytes and hashes in original recorded evidence. All 44 retained processes map to shipped workers: 14 launch-only records and 30 runtime self-hash records. The weaker early attestation is disclosed; no claim of independent environment attestation is made. |
| Frozen artifacts | All 494 recorded frozen-file digests match disk. All 36 source/generated digests in the paper asset map match. Raw/scored output preservation was checked separately. |
| Archive integrity | 611 archive files; all 610 entries in the internal checksum manifest verify. External checksum matches the archive. Existing source files in the archive match disk. Only an empty `HF_TOKEN` template `.env.example` is included; no actual `.env`, credential store, model weights, or environment cache was found in the package paths. |
| Availability/publication | The public GitHub repository returns HTTP 200 and GitHub API metadata says `private: false`. The remote candidate tag and GitHub release endpoints return 404, consistent with the manuscript’s explicit pending-publication statement and the instruction not to publish yet. These expected 404s are not broken advertised release links. |
| Links | All 12 unique PDF annotation URLs return HTTP 200. Current documentation destinations resolve locally. Historical snapshot navigation is finding 5; the link scan checks destinations, not every Markdown anchor. |
| Tests | Independently rerun: **56 passed** with bytecode/cache writes disabled and temporary test files directed outside the repository. Tests use synthetic/stubbed execution; no study job was launched. |

Audited PDF SHA256:

```text
717c34cd26ca7f66ef27a534255feb8d050df812da4b90c7b2763cac96f3bf72
```

Audited research archive SHA256:

```text
8b3115a18adcf283b63526f1741be0b8981894241f6ce88a3049b606dae3deb4
```

The current archive still says the fresh-session audit is pending; that is expected for this untouched candidate. Any approved revision should produce a newly identified candidate and refreshed PDF/archive checksums. This audit neither changes the existing tag nor authorizes publication.
