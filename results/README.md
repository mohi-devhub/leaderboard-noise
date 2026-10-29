# Research artifact layout

The [combined A10/L4 report](REPORT.md) is the numerical entry point for the [merged article](../blog/STUDY.md). It uses saved artifacts only, labels every confidence interval exploratory, and names the higher-ranked model for every default GPU/batch configuration. Per-session reports below remain frozen provenance.

The [six-model A10 study](REPORT.md) completed with 58,800 scored predictions, including 48,000 primary and 10,800 timing outputs. Its [receipt](study-20261028T065939Z/receipt.json) records app-specific metering, conservative estimates, released reservations, and shutdown. See [final status](FULL_STUDY_STATUS.md) and the [article](../blog/STUDY.md).

The [earlier A10 pilot](pilot-20261028T050156Z/REPORT.md) contains 3,200 separately scored predictions. Historical approval gates in pilot and failed-attempt documents do not describe the completed study's current status.

- `audit-local.json`, `audit-bfcl.json`, `audit-gpu.json`: machine-readable dependency audits. GPU has exactly the documented accepted setuptools exceptions; inspect SECURITY.md.
- `metadata/`: verified model license sources, dependency release dates, and authenticated Modal rate fields.
- `security/`: primary advisory records supporting the applicability review.
- `budget-ledger.json`: conservative reservations, separate from invoices and timed estimates.
- `pilot-<UTC timestamp>/`: per-session billing snapshots, raw model/arm results, scored JSONL, analysis reports, and shutdown evidence when a session reaches those stages.
- `study-20261028T065939Z/`: six complete model JSON files with metadata, raw/scored JSONL, primary-only `evaluation.jsonl`, condition-specific analyses, all 15 pairwise flip comparisons, repeated throughput, verified-download receipts, source correction snapshots, and budget/shutdown evidence.

The first session was cancelled during setup to correct seeded request broadcasting. No benchmark predictions from that setup are used. A session directory or a reserved budget entry does not mean a model has been evaluated. Only `REPORT.md` produced after complete coverage validation denotes a completed pilot analysis.

Model artifacts include exact decoded outputs, generated token IDs, truncation flags, checkpoint revisions, message and rendered-prompt hashes, package versions, and timing. No secrets belong in these files. Benchmark files/IDs and their hashes are frozen in `experiments/` before evaluation. Figures must be generated from a recorded analysis JSON, never drawn from guessed model scores.

The [L4 follow-up status](L4_FOLLOWUP_STATUS.md) records the completed two-pair replication. The primary pair was preserved under `l4-followup-20261028T190732Z/` after preemption. `l4-continuation-20261028T224638Z/` retains those exact checkpoints and collected only the unfinished pair; its report combines the four models and compares A10. Partial uncheckpointed work is not scored. Per-pair UUIDs, execution claims, app-specific receipts, and archived volume sidecars identify the two allocations.
