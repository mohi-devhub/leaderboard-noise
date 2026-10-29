# Budget ledger

## Approved continuation running

The user approved the remaining-five $6.5151 forecast. It is running detached with one server controller and one A10 input; all budget checks execute on the server. A conservative $9.51875025 reservation remains active while usage accrues. Prior estimated spend, including a $0.01 cloud-pin setup rejection before any input, is $1.20013614. Prior estimate plus the active bound is $10.71888639, below the $12 project cap. A laptop disconnect does not trigger cleanup of an active remote job. This reservation is not billed spend and will be released after resource reconciliation.

## Current status after the interrupted full-study session

Only Qwen2.5-1.5B completed the full 500-item protocol, including three timing repetitions. Its execution took 2,053.81s versus 2,072.68s forecast. App-specific gross metering is $0.75502874; the conservative stopped-app resource estimate plus margin is $0.86659479. The ledger excludes subsequent client waiting after Modal stopped the app. Including prior attempts, cumulative estimated project spend is **$1.19013614**, with zero reservations. Invoice actuals remain unknown.

The completed model's 9,800 outputs are preserved and scored. No second model call was accepted. One fresh connection recovered the completed call, but the stopped app could not accept further work. No completed job is resubmitted.

The prepared remaining-five job forecasts **$6.51508230**, with a **$9.51875025** conservative bound including bounded GPU startup and CPU orchestration. Expected and conservative project totals are **$7.70521844** and **$10.70888639**. This is one durable job above the user's $5 threshold, so explicit approval is pending. It has not launched. The resource bound includes server-side per-model gates, a whole-job deadline, and the 30-minute allocation guard. See `results/study-20261028T065939Z/remaining-forecast.json` and `scripts/run_remaining.py`.

Authorization: October credits expire October 31. Gross compute cap **$12**, independent of credit offsets. Ask before a batch projected over **$5**. The user approved the full six-model A10 study on October 28 after reviewing the pilot. No unattended recurring jobs.

## Approved full-study forecast, October 28

The six sequential model batches forecast **$7.3310** in new study spend. Conservative bounded allowances plus setup/egress total **$9.8744**. With prior estimated spend of $0.3035, expected and conservative project totals are **$7.6346** and **$10.1780**. Individual model allowances are $1.14–$2.16, below the $5 threshold. Forecasts derive from measured A10 pilot timings, with explicit extrapolation factors for unmeasured models. They are not actual charges. See `experiments/full-forecast.json` and [the frozen plan](docs/FULL_STUDY_PLAN.md).

Recheck cumulative resource estimates after every model and stop before a next batch would cross $12. An independent watchdog bounds each model's execution. A10 only, 30-minute allocation cutoff, one container at a time. Account deltas include parallel qunti-check usage, so use attributed timings and tagged metering rather than charging unrelated work to this project. Settled invoice actuals remain unknown until supplied by Modal.

## Rates and reservation

`results/metadata/modal-rates.json` records the authenticated `modal billing rates --json` response fields retrieved 2026-10-27: L4 $0.80/GPU-hour, physical CPU $0.04730/core-hour, RAM $0.008/GiB-hour, egress $0.04/GiB. [Modal pricing](https://modal.com/pricing) describes billing during startup and idle timeout. These are rates, not measured run costs.

Worker request: one L4, at most four physical CPU cores and 16 GiB host RAM, one container and zero retries. A 30-minute timeout at those resource ceilings gives a resource estimate of `(0.80 + 4*0.04730 + 16*0.008)*0.5 = $0.5586` per model call, before build/startup/egress. This is not a guaranteed invoice cap; platform billing can include startup and orchestration outside the function timer.

Conservatively reserve **$4.50 for the approved pilot retry**, including the CPU image build, initial five-request smoke test, and both default and mitigation arms for each model. All GPU calls are sequential on at most one L4 container. Charge completed failed attempts using their recorded estimated spend and release unused holds, per the user's explicit accounting instruction. Invoice actuals remain a separate field. Do not retry infrastructure failures. Use no persistent model volume; termination avoids lingering storage charges.

Pilot workload: 2 models ×100 items ×10 stochastic completions = **2,000 planned stochastic completions**; three greedy configurations ×2 arms ×2 models ×100 = **1,200 planned greedy completions**, plus five smoke requests per model/arm and warmup. These are planned counts, not completed observations. Token cap 512 does not predict actual generation length or throughput. A full six-model/500-item estimate must use measured pilot time and cannot be approved merely by scaling this reservation.

## Current status

| Stage | Projected/reserved USD | Actual invoice USD | Status |
|---|---:|---:|---|
| Literature, local CLI/tests | 0 Modal spend | Local CPU only | Completed local work |
| Cancelled initial setup | 0.01019379 estimated spend; no hold | Pending | Provisional account-delta estimate; no concurrent app observed |
| Failed initial L4 attempt | 0.02070498 estimated spend; no hold | Pending | Timed resource estimate; no predictions, second model never invoked |
| Approved compiler-fix retry | 0.01019913 estimated spend; no hold | Pending | CPU preflight/audit passed; app disconnected before first L4 smoke submission |
| Successful October 28 A10 pilot | 0.26244345 estimated spend; no hold | Pending | 3,200 scored predictions; one job/container; stopped |
| Full six-model experiment | Not yet estimated | Not run | Requires post-pilot OK |
| Optional EvalPlus | Not yet estimated | Not run | Evaluate within remaining cap after pilot |

The pre-project account billing summary includes unrelated prior usage; do not attribute it to this project. Record a billing baseline immediately before launch and a post-session summary separately. Their difference is usable only if there is no concurrent unrelated activity and the meter has settled. Record timed resource estimates separately from invoice actuals. Never turn a missing or delayed invoice into a fabricated zero.

`results/budget-ledger.json` separates estimated spend, temporary reservations, and invoice actuals. Budget checks add prior estimated spend plus active reservations; they reject a batch over $5 or total exposure over $12. After each session stop only this evalnoise app and record app-state evidence. The user explicitly instructed us not to stop or modify `qunti-check-pilot`, which belongs to another project.

The earlier $9 then $4.50 reservation holds are historical, not spend. The user directed release of all unused holds. Prior failed/setup attempts total **$0.04109790** in estimates. The successful October 28 pilot adds **$0.26244345**. **Current total recorded estimated spend: $0.30354135; active reservations: $0.** Actual project invoice costs remain unknown. The pilot authorization is consumed; the full study has not been launched.

The cancelled setup's gross metered account snapshots rose from $1.90365003 to $1.91384382, a **$0.01019379 account-level change**, with $0 billed after credit offsets. The corrected attempt's snapshots rose to $1.92396832, a further **$0.01012450 account-level change**. A concurrent unrelated app appeared, and metering can lag; these are not settled project invoices. Do not attribute account deltas to evalnoise or equate credit-offset billed cost with gross compute cost.

## Initialization failure and timing

See [the failure report](results/pilot-20261027T131052Z/FAILURE_REPORT.md). One L4 call started after a 847.451-second queue/provisioning interval and failed after 58.486404 seconds of execution because Triton had no C compiler. The container startup statistic was 6.232109 seconds. No smoke-test or benchmark predictions completed; model 2 never ran.

Execution + observed startup + configured 2-second scaledown, at the resource ceilings above, gives a **$0.020705 timed resource estimate**, excluding image builds, egress, and metering differences. Actual project invoice cost remains unknown. This is an infrastructure failure, not a scientific null result. The compiler fix and one retry were subsequently approved. The full six-model projection still waits for a successful pilot and explicit user approval.

The corrected runner has a separate initial five-request smoke call and saves each model/arm result incrementally. Each arm call has a 30-minute function timeout; its subprocess stops at 29 minutes. The smoke subprocess has a 10-minute timeout. Five total calls at these bounds would have a resource-ceiling estimate of about $2.42 before image builds and provisioning overhead, inside the $4.50 batch reservation. Queue delay is reported separately from measured generation time. Tagged future billing may improve attribution; concurrent unrelated app usage still prevents assigning raw account deltas to this project.

## Approved retry outcome

See [the latest failure report](results/pilot-20261027T144048Z/FAILURE_REPORT.md). The corrected image passed its CPU compiler/headers test and actual Python dependency audit. Modal subsequently logged `local client disconnected` and rejected the first smoke submission with `ConflictError: The app is stopped or disabled`. Function history records **zero calls and zero GPU containers**, so no smoke or benchmark predictions completed. The disconnect's underlying cause is unconfirmed.

The retry's account snapshots changed from $2.03436545 to $2.04456458. The $0.01019913 difference is a provisional estimate, not a settled project-specific invoice. The unused $4.50 reservation is fully released. This evalnoise app is stopped. No `qunti-check-pilot` app was stopped or modified, and no second retry was submitted.

## October 28 approval

The user subsequently approved one new pilot attempt, with **L4 preferred and A10 fallback**, and one connection-only retry. App listing showed no running apps and the configured token authenticated; no credentials were printed or changed. A fresh context-managed client is used. The immutable compiler-equipped image is reused with a fresh CPU preflight and audit.

The initial five-request smoke test and all model/arm stages are now one detached, bounded call. This is one job submission, with the call ID saved before waiting. A disconnect allows one fresh connection to that ID, never a second job submission. GPU preference is resolved once for the container, so all arms and both models use the same GPU. Actual GPU name is recorded; scientific and throughput conclusions are restricted to that hardware. The separate qunti-check project is preserved.

At launch the batch reserved **$4.50**, making estimated spend plus reservation **$4.54109790**. Authenticated rates remain L4 $0.80/hour and A10 $1.10/hour, CPU $0.04730/core-hour and RAM $0.008/GiB-hour. The single-call 90-minute timeout gave a resource-ceiling estimate of $1.6758 on L4 or $2.1258 on A10, before overhead. The unused hold is now fully released.

## Completed pilot: October 28

[Report](results/pilot-20261028T050156Z/REPORT.md) and [machine-readable receipt](results/pilot-20261028T050156Z/receipt.json). Modal selected **NVIDIA A10**. One job, one container, no reconnect, no job resubmission. Five initial smoke requests passed, followed by all 3,200 benchmark predictions. Remote execution took **591.57 seconds**; controller wall time before cleanup was **636.74 seconds**. The app stopped before October 31; no unrelated app was modified.

Applying the A10/CPU/RAM resource ceilings to execution + 10.02 seconds of observed container startup + two seconds of scaledown gives **$0.23761459**. Account metered cost increased from $2.27457565 to $2.53701910, a **$0.26244345** gross change. Use the larger figure as the conservative provisional session estimate; invoice attribution remains unsettled. Total recorded project estimate is **$0.30354135**, well below $12, with no active reservations.

Future full-run estimates must use the pilot's separate startup/warmup/generation timings and account for the unmeasured larger models, different output lengths, and gated access. The full six-model and optional code phases remain unapproved. No general A10-versus-L4 throughput claim or guaranteed full-run cost follows from this pilot.
