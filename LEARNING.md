# Learning notes

**Pass@1** asks: how often does one generated answer pass? With ten independent answers to each question, average the ten pass/fail outcomes, then average across questions. Ten answers do not make ten new questions.

**Pass@k** asks: if we could try k answers and recognize a correct one, how often would at least one succeed? Counting all k-sized subsets of n observed answers gives `1 - C(n-c,k)/C(n,k)`. It avoids the bias of simply treating the first successful attempt as representative. It needs n>=k and iid attempts. It says nothing about how to select the correct answer without checking it.

**Bootstrap** means replaying the evaluation with replacement from observations we already have. For item uncertainty, draw question IDs with replacement. Keep each selected question's answers together and draw the same IDs for both models. That pairing preserves which questions both models find difficult. Resampling all individual answers as unrelated questions exaggerates the information available.

**Confidence intervals** describe a procedure's long-run coverage under its assumptions. A 95% procedure should cover the target in roughly 95% of hypothetical repetitions. It is not a 95% probability statement about this particular fixed interval. Bootstrap intervals may misbehave when very few items vary, or every observed answer passes/fails.

**Greedy decoding can change** even at temperature zero. Greedy picks the largest computed next-token score. Batch-dependent numerical computations can slightly change those scores. Near a tie, that can select a different token, which changes the rest of the answer. A seed controls random draws, not every numerical kernel. Batch-invariant computations aim to remove dependence on neighboring requests; their speed and effectiveness must be measured for the actual setup.

**Reading comparisons:** look at the paired difference CI, not just whether two separate CIs overlap. A bootstrap win fraction near one means the order is stable under that resampling scheme. Always inspect ties, item count, generation count, decoding configuration and whether the comparison was chosen after seeing the data. An output may change without affecting correctness or rank.

**Uncertainty in a flip rate:** there are two different questions. Repeating a bootstrap with more computer-generated draws makes its estimated fraction more precise on the same observations. A Monte Carlo interval describes that precision. Evaluating different benchmark questions can change the flip fraction itself. Our outer paired-item bootstrap explores that second uncertainty by recomputing the fraction on resampled question sets. Its percentile interval is exploratory, especially near tied scores or zero flips. More computer-generated resamples do not replace collecting more questions, and a collapsed interval cannot rule out outcomes absent from the observed data.

**Minimum detectable difference (MDD)** is an approximate planning threshold for an assumed effect, test level and power. More items reduce both item and prediction uncertainty. More generations per item reduce prediction uncertainty but hit a floor from differences between questions. A pilot helps choose where the next dollar goes; it does not guarantee a significant result.

## Explain in two minutes

A leaderboard score is the result of a measurement, and measurements have noise. A model may look better because the chosen questions favor it, because sampled answers happened to succeed, or because the inference engine calculated slightly different outputs under a different batch.

We test the same questions on both models. We generate several answers per question to see sampling variation. Then we bootstrap question IDs, keeping answers together, to see how often the apparent winner changes. We also repeat greedy decoding under controlled batch settings and test a batch-invariant setting. We count changed outputs, changed correctness and changed rankings separately, and measure speed.

In our six-model A10 study, Llama3B stayed at 457 correct calls while Qwen3-4B scored 458, 457, and 456 at increasing batch sizes. That changed the observed winner by one question. Batch invariance kept their scores stable, but reduced median token throughput by about 32–60% across the tested configurations. Their paired score-difference intervals include no difference. “Inconclusive at this budget” is different from proving the models are equal.

## Five interview questions

1. **Why pair the bootstrap across models?** The same question can be easy or hard for both. Pairing preserves that relationship and estimates the uncertainty of their difference directly.
2. **Why not call ten completions ten independent items?** They share a question. Their common difficulty creates dependence when reasoning about an unseen question population.
3. **Is pass@10 the same as taking ten times pass@1?** No. Pass@10 is the probability that at least one candidate works; it saturates at one and requires a way to recognize correctness.
4. **Does temperature zero guarantee repeatability?** No. It removes intentional token sampling. Batch-dependent arithmetic and near-tied logits can still change greedy choices.
5. **What if batch invariance produces no ranking improvement?** Report it. Perhaps outputs already agree, changes do not affect correctness, or the scores are too far apart to flip. Measure throughput and state exactly what the pilot can establish.

## Reading our completed six-model study

The study contains 58,800 scored outputs, including 10,800 timing outputs. The primary sampling comparison still has 500 questions with ten answers per question per model. Timing repetitions verify work and speed; they do not create new independent questions.

Two pairs had default serial greedy scores within three percentage points. Qwen2.5-3B versus Qwen3-1.7B had a 13.18% bootstrap batch-flip fraction, with an exploratory interval of 0.60–35.80%. Llama3B versus Qwen3-4B had 8.94%, with 0.50–23.66%. Only the latter flipped on the actual full 500-question set. A bootstrap fraction answers what happens when the question mix changes; it is different from counting a flip in the observed dataset.

Both invariant flip fractions were zero, with collapsed outer intervals. Those intervals cannot rule out patterns absent from our data. Each model also had zero observed invariant text changes across the three batch sizes, with a Wilson upper bound of about 0.76% under the independent-item approximation. That is useful evidence for this A10 setup, not a guarantee for every request schedule or GPU.

The three pairs chosen from published leaderboard scores turned out to be more than three points apart on our common-prompting subset. The close pairs found here are exploratory comparisons. We kept every preselected pair and all other pairs in the report rather than replacing models to manufacture a flip.

For stochastic pass@1, the approximate minimum detectable gaps at 500 questions and ten answers were 4.45 percentage points for Qwen2.5-3B versus Qwen3-1.7B, and 3.87 points for Llama3B versus Qwen3-4B. Under these variance estimates, a three-point target requires about 1,100 and 834 questions, respectively, at ten samples per model. Increasing answers alone at the existing 500 questions cannot reach that target because item variation remains. These are planning approximations, not guaranteed outcomes.

The [article](blog/STUDY.md) and [full report](results/REPORT.md) include all per-model text intervals, three-repetition timing ranges, sampling scores, and cost evidence.

## Reading the earlier A10 pilot

The 100 questions produced 1,000 sampled answers per model. Qwen0.5B scored 51.9% pass@1, with an item-bootstrap 95% interval of 44.1–59.6%; Qwen1.5B scored 83.9%, with 78.0–89.4%. The information for question-set uncertainty is organized around **100 questions**, not 1,000 unrelated observations.

Default greedy text changed across batch settings on 11 questions for 0.5B and three for 1.5B. With batch invariance, neither model's text changed on any of these 100 questions. Correctness varied across batches on three 0.5B questions and none of the 1.5B questions. The larger model stayed ahead throughout. This demonstrates why changed text, changed correctness, and changed rank must be counted separately. Zero changes in this pilot does not establish universal determinism.

The estimated minimum detectable pass@1 gap at this design was about 10.8 percentage points. Under these pilot variance estimates, a five-point target gap needs about 470 items at ten samples/item/model. Increasing samples alone at the same 100 items could not reach that target because question variability remains. These are approximate projections under the same variance assumptions; they are not guarantees for different or closer model pairs.

The pass@5/pass@10 headline intervals resample items. Conditional within-item resampling for k>1 is labeled diagnostic because finite-repeat bootstrap bias can be substantial; it should not be treated as a calibrated confidence interval. See the [report](results/pilot-20261028T050156Z/REPORT.md) for the measured numbers and limitations.

## What the L4 replication adds

The Llama3B/Qwen3-4B ranking also flipped on an L4, but in the opposite direction. At batch sizes 1, 8, and 32, A10 default decoding favored Qwen, tied, then favored Llama. The L4 favored Llama, tied, then favored Qwen. The replication supports the claim that batch settings can change the observed winner; it does not reproduce the same winner at each setting. Both invariant arms held Llama at 458 and Qwen at 457 correct answers on both GPUs. Those one-answer edges still do not establish superiority on unseen questions.

Within-GPU batch invariance and cross-GPU agreement are separate questions. Stable scores can also hide changed text on individual questions. The saved reports therefore count text changes, correctness changes, and ranking changes separately. Two L4 allocations were needed after preemption; each requested pair and its two arms share one physical card. Generation history, host settings, and drivers also differ from the A10 session, so this is a replication on the recorded setups rather than a clean causal test of GPU architecture alone.

The second pair, Qwen2.5-3B versus Qwen3-1.7B, did not flip on the actual 500-item set on either GPU. Its bootstrap flip fraction was 13.18% on A10 and 8.48% on L4, with exploratory 95% intervals of 0.60–35.80% and 0.70–28.45%. A nonzero bootstrap fraction can coexist with no actual full-set flip: the resampled question mix differs. All four models' invariant outputs matched across A10 and L4 in this experiment. See the [L4 article](blog/STUDY.md) for the complete comparison.
