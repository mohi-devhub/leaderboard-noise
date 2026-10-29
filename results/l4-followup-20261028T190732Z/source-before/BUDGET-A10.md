# Budget ledger

## Completed project within the $12 cap

The conservative recorded project estimate is **$7.56377144 of $12**, including the pilot, setup failures, preserved model, and detached remaining-five continuation. Active reservations are **$0**. All study apps are stopped with zero running containers. The temporary results volume was deleted after SHA256 verification. The separate qunti-check project was not modified.

Compute finished October 28, before the October 31 credit deadline. Final analysis and documentation were completed October 29 in Asia/Kolkata. Credits are a payment offset and do not reduce the gross-compute cap. Settled invoice actuals remain unknown.

## Forecast versus measured cost

| Scope | Forecast USD | App-specific gross metering USD | Conservative recorded estimate USD |
|---|---:|---:|---:|
| Approved remaining-five job | 6.51508230 | 5.60078037 | 6.36363530 |
| Six-model study, including preserved model and provider-pin setup | 7.33102744 | 6.35595139 | 7.24023009 |
| Whole project, forecast at continuation approval | 7.71521843 | Not fully attributable for early attempts | 7.56377144 |

App-specific gross metering is provisional and may lag. It excludes credit offsets and unrelated qunti-check usage. Conservative estimates use the larger of attributed metering and bounded resource-time estimates plus startup/setup margins. They are distinct from reservations and settled invoices. Early setup estimates have the limitations recorded in the ledger; missing invoices are never recorded as zero.

The remaining-five job ran one GPU input for 15,813.79 seconds, about 4.393 hours. The six models together used 17,845.29 seconds of measured model execution, about 4.957 hours. The [receipt](results/study-20261028T065939Z/receipt.json) lists forecast and measured time and resource costs for every model. It includes startup and orchestration in session accounting; post-stop local waiting and CPU analysis do not extend GPU residency.

## Decisions and bounded exposure

The user approved the six-model study after reviewing the two-model pilot, then explicitly approved the $6.52 remaining-five job because it exceeded the $5 batch threshold. That continuation preserved model one and used a detached server-side controller, one A10 GPU input, per-model checkpoints, and no GPU job retries. The local observer reconnected once after a temporary volume-read error while the original GPU call continued.

Before continuation, estimated spend was $1.20013614. The conservative reservation was $9.51875025, giving maximum planned exposure of $10.71888639. That reservation was an allowance rather than an actual charge and is now fully released. Failed attempts are charged by estimated spend, including about $0.02 for the compiler failure, rather than their former $4.50 holds.

The server checked cumulative resource estimates plus the next bounded model allowance before each of the five models. All five gates are archived in [remaining-budget-checks.json](results/study-20261028T065939Z/remaining-budget-checks.json), with original log lines. The final gate was $6.085258 plus $2.158162, or $8.243420, under the $12 cap. Per-model deadlines, a whole-job watchdog, and a 30-minute A10 allocation cutoff bound execution independently of the laptop.

## All project attempts

| Stage | Recorded estimated spend USD | Reservation USD | Status |
|---|---:|---:|---|
| Initial cancelled setup | 0.01019379 | 0.00 | setup_cancelled_before_gpu_generation |
| L4 missing-compiler attempt | 0.02070498 | 0.00 | failed_no_automatic_retry |
| Compiler-fix image; disconnect before submission | 0.01019913 | 0.00 | infrastructure_failure_before_l4_smoke_submission |
| Successful two-model A10 pilot | 0.26244345 | 0.00 | pilot_validated_waiting_for_full_run_approval |
| A10-tier name guard before inference | 0.02000000 | 0.00 | gpu_name_guard_failed_before_inference |
| Preserved Qwen2.5-1.5B full protocol | 0.86659479 | 0.00 | stopped_incomplete_no_job_retry |
| Unsupported provider pin before submission | 0.01000000 | 0.00 | cloud_pin_rejected_before_submission |
| Detached remaining-five A10 job | 6.36363530 | 0.00 | full_study_scored_apps_stopped |

The pilot has 3,200 scored predictions. The full study has 48,000 primary predictions and 10,800 separately scored timing outputs. Setup failures without completed benchmark generations are infrastructure outcomes, not scientific null results. Optional EvalPlus execution was not launched and has no recorded Modal spend.

## Rates and evidence

Authenticated rates were retrieved October 27. A10 is $1.10 per GPU-hour, physical CPU $0.04730 per core-hour, and RAM $0.008 per GiB-hour. The worker is bounded at four CPU cores and 16 GiB RAM, giving a resource ceiling of $1.4172/hour. The small server controller adds a ceiling of $0.015825/hour. The reservation also covers startup, allocation control, setup, and egress margins. These ceilings exceed actual resource consumption and are not invoice charges. Original pilot L4 rates and provisioning failures remain in the historical evidence.

- [Machine-readable ledger](results/budget-ledger.json) separates estimates, released reservations, and unknown invoice actuals.
- [Final study receipt](results/study-20261028T065939Z/receipt.json) and app-specific billing exports attribute usage by exact owned app IDs.
- [Original full forecast](experiments/full-forecast.json) and [approved continuation forecast](results/study-20261028T065939Z/remaining-forecast.json) preserve assumptions before launch.
- [Shutdown evidence](results/study-20261028T065939Z/remaining-shutdown.json) and verified-download receipts document cleanup.
- [Historical budget snapshot](results/metadata/BUDGET-before-final.md) preserves intermediate estimates and the earlier failure narrative.

No further inference job or unattended schedule was launched.
