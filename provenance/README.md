# Executed-source provenance

Files are copied byte for byte from saved sources whose hashes match recorded launch or runtime evidence. `manifest.json` maps each retained process to its matching worker. Early A10 processes are launch-attested only; later A10 and L4 worker self-hashes are checked. Normalized serialized A10 function snapshots are shipped alongside full launcher/worker sources. The Llama BOS correction has separate before/after files.

Do not format or modify these snapshots. They preserve executed/submitted code, including historical style and dependencies. Check `SHA256SUMS`; read each attestation label before claiming runtime coverage. These hashes are not third-party signatures.

## Historical document navigation

Historical Markdown copies retain their original bytes and relative links. Open those links relative to the original location below, rather than the nested snapshot directory. The linked current documents provide working navigation; the snapshots remain evidence of what existed before execution or recovery.

| Historical copy | Original location | Current document |
|---|---|---|
| `results/l4-followup-20261028T190732Z/BUDGET-before-preemption.md` | repository root `BUDGET.md` | [Budget](../BUDGET.md) |
| `results/l4-followup-20261028T190732Z/source-before/BUDGET-A10.md` | repository root `BUDGET.md` | [Budget](../BUDGET.md) |
| `results/l4-followup-20261028T190732Z/source-before/README.md` | repository root `README.md` | [README](../README.md) |
| `results/l4-followup-20261028T190732Z/source-before/STUDY.md` | `blog/STUDY.md` | [Study](../blog/STUDY.md) |
| `results/metadata/BUDGET-before-final.md` | repository root `BUDGET.md` | [Budget](../BUDGET.md) |

For example, resolve a snapshot's `results/study-20261028T065939Z/receipt.json` from the repository root. Resolve `../results/...` in the copied study from `blog/`. Historical approval statements and document digests describe their original dates. The current paper, article, report, and release documentation contain the audit corrections; the archived copies do not receive editorial updates.
