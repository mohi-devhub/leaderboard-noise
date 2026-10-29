# Approved retry: CPU preflight passed, Modal lifecycle failure

The one authorized retry stopped on an infrastructure failure before the first L4 smoke invocation was accepted. No further retry was submitted.

## What passed

- The corrected image installed pinned official Debian `build-essential=12.12`.
- The CPU preflight found GCC and successfully compiled a source including Python.h.
- Hash-locked Python packages installed from official PyPI.
- The actual image audit completed with zero unaccepted findings and the three entries covered by the two documented setuptools advisory exceptions.
- Final worker image: `im-lrHUA0egLqd897fDW0kqQ9`. Compiler preflight and audit evidence are in `preflight-evidence.txt` and the complete `build-and-failure.log`.

## Where execution stopped

Modal reported `Stopping app - local client disconnected`. The initial `run_model.spawn(...)` then failed with `modal.exception.ConflictError: The app is stopped or disabled`. Modal lifecycle records show the app stopped with `stopped_by: null`. The underlying disconnect cause is unconfirmed; no model or mitigation failure can be inferred.

The function history records **0 calls** and **0 GPU containers**. Completed smoke requests: **0**. Completed benchmark predictions: **0**. No score, CI, throughput, rank-flip, or MDD measurement is available for the research pilot.

## Accounting

The original failed L4 attempt is counted at its recorded **$0.02070498 resource estimate**, not its reservation. The initial cancelled setup has a **$0.01019379 provisional estimate**. This retry's account gross-metered delta is **$0.01019913**, recorded as a provisional CPU-build estimate rather than a settled invoice. Account metering can lag and include prior unrelated usage; invoice actuals remain unknown. Credit-offset billed cost is not gross resource cost.

All unused reservations are released. Total recorded estimated spend across the three attempts is **$0.04109790**; active reservations are **$0**. The $12 cap is unchanged.

## Shutdown and scope

This evalnoise app is stopped, as are prior evalnoise apps. `qunti-check-pilot` was neither stopped nor modified by this retry. `shutdown.json` and `apps-after.json` preserve the read-only app-state evidence. No further compute is authorized under the consumed single-retry approval.

## Local verification

Fifteen local tests pass, including seed-index preservation and cleanup isolation. Lint and format checks pass. The official BFCL checker smoke fixtures pass on CPU. The scientific pilot remains unfinished; this is an infrastructure failure report, not an empirical null result. The full six-model experiment remains gated.
