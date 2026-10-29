# Pilot status

**Pilot completed October 28, 2026, before the October 31 deadline.**

The October 28 approval ran one detached job on the NVIDIA A10 fallback, with the same GPU for both models and both arms. Five initial smoke requests passed, followed by all 3,200 benchmark predictions. The official BFCL scorer and coverage validator passed; no completions were truncated.

Default greedy text changed across batch sizes on 11/100 items for Qwen0.5B and 3/100 for Qwen1.5B. The invariant arm changed 0/100 for both. Neither arm showed a ranking reversal; the pilot models were separated by a large score gap. These observations are specific to A10 and the pinned configuration.

[Complete report](pilot-20261028T050156Z/REPORT.md), [receipt](pilot-20261028T050156Z/receipt.json), [figures](../figures/pilot-20261028T050156Z).

Estimated session spend is $0.26244345; cumulative estimated project spend is $0.30354135, with invoice actuals still unknown. All reservations are released. The app is stopped, no connection retry was needed, and the separate qunti-check project was not modified. The full six-model study has not been launched and awaits the user's OK.

Earlier infrastructure failures are retained in their original session directories; they are not scientific null results.
