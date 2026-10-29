# Pilot attempt: initialization failure, no benchmark results

The first L4 worker failed before the five-request smoke test or any benchmark generation. Triton reported `Failed to find C compiler`. This is an infrastructure failure, not a null scientific result and not evidence about model quality or mitigation effectiveness.

- Queue/provisioning interval: 847.451 seconds (about 14 minutes 7 seconds).
- Model-call execution before failure: 58.486404 seconds.
- Container startup statistic: 6.232109 seconds.
- Completed smoke requests: 0. Completed benchmark predictions: 0.
- Model 2 was never invoked. No CIs, rank-flip odds, MDD estimates, or empirical figures are available for this pilot.

## Cost

Timed resource estimate: **$0.020705**, applying the configured ceiling of one L4, four physical CPU cores, and 16 GiB RAM to execution + observed startup + two seconds of scaledown. It excludes image building, egress, and differences in actual metering; it is not an invoice actual.

Account gross metered change during this attempt: **$0.01012450**. An unrelated `qunti-check-pilot` app appeared during the session, and billing can lag, so this account delta cannot be assigned to evalnoise. The workspace's billed-after-credits snapshot is zero, which is not evidence of zero gross project usage.

Original reservations were $4.50 for each two-model attempt. Each attempt stopped during its first-model call; release only the never-invoked second model's $2.25 reservation. Retain $2.25 per attempt, **$4.50 total**, pending invoice reconciliation. A new two-model attempt would reserve $4.50, bringing the total retained reservation to $9, below the $12 project cap. No retry is authorized or launched.

## Prepared correction and validation

The runner now adds official Debian `build-essential=12.12` and a CPU image-build preflight that compiles C including Python.h. This should address the observed missing-compiler prerequisite, but the corrected image has not been built or validated on an L4. Do not describe the fix or batch-invariant arm as working yet. Local CLI validation: 14 tests pass, lint/format pass, package builds. The official BFCL checker fixtures pass under the security overrides. See SECURITY.md for the 20 original BFCL audit entries, fixed versions, and the two explicitly accepted setuptools advisories.

Stopped further compute because the user instructed us to stop and report if vLLM breaks. Both evalnoise apps are stopped. A separate active app requires the user's cleanup-scope decision; see shutdown evidence. The full experiment still requires post-pilot approval, and this failed attempt does not satisfy that pilot gate.

## Evidence

- `failure.log`: remote exception and engine initialization trace.
- `final-calls.json`, `final-stats.json`: timings and failure state.
- `billing-before.json`, `billing-after.json`: account snapshots, not project invoices.
- `failure-summary.json`: structured summary.
- `shutdown.json`: app-state evidence and cleanup scope.
