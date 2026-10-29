# Dependency and execution security record

Reviewed October 27–28, 2026. Secrets belong only in gitignored `.env` or the existing Modal credential store. No secret values are printed, copied to run metadata, or committed. Public pilot models require no Hugging Face token. Model weights use fixed official repository revisions with `trust_remote_code=False` and safetensors; no model-supplied Python is enabled.

## BFCL: 20 original findings in two packages

The first BFCL lock inherited exact upstream pins `datamodel-code-generator==0.25.7` and `filelock==3.20.0`. `pip-audit` reported 20 entries, including repeated aliases. No affected BFCL environment was used for inference. Security-only overrides retain the official BFCL wheel and change its dependencies:

| Package | Original | Selected fix | First PyPI upload | Cooldown |
|---|---|---|---|---|
| datamodel-code-generator | 0.25.7 | 0.64.0 | 2026-06-14 | >=14 days |
| filelock | 3.20.0 | 3.20.3 | 2026-01-09 | >=14 days |
| pytest (local tools) | 9.0.2 | 9.0.3 | 2026-04-07 | >=14 days |
| python-dotenv (local tools) | 1.2.1 | 1.2.2 | 2026-03-01 | >=14 days |

Advisories for datamodel-code-generator: [GHSA-j884-q54q-mmx3](https://github.com/advisories/GHSA-j884-q54q-mmx3) (PYSEC-2026-3561, CVE-2026-54621), [GHSA-r5vv-ff45-prp2](https://github.com/advisories/GHSA-r5vv-ff45-prp2) (3563, CVE-2026-55403), [GHSA-5578-w22f-pfx9](https://github.com/advisories/GHSA-5578-w22f-pfx9) (3557, CVE-2026-55415), [GHSA-rfr2-mq9m-x2qx](https://github.com/advisories/GHSA-rfr2-mq9m-x2qx) (3564, CVE-2026-54691), [GHSA-954p-556p-r752](https://github.com/advisories/GHSA-954p-556p-r752) (3560, CVE-2026-54690), [GHSA-vx7x-vcc2-c44g](https://github.com/advisories/GHSA-vx7x-vcc2-c44g) (3565, CVE-2026-55391), [GHSA-386q-5hp3-95m9](https://github.com/advisories/GHSA-386q-5hp3-95m9) (3555, CVE-2026-54653), and [GHSA-wjv6-jcfj-mf9r](https://github.com/advisories/GHSA-wjv6-jcfj-mf9r) (3566, CVE-2026-54654). Numeric abbreviations in parentheses refer to PYSEC-2026 IDs.

Filelock: [GHSA-w853-jp5j-5j7f](https://github.com/advisories/GHSA-w853-jp5j-5j7f) / CVE-2025-68146 and [GHSA-qmgc-5h2g-mvrw](https://github.com/advisories/GHSA-qmgc-5h2g-mvrw) / CVE-2026-22701. Local tool fixes address PYSEC-2026-1845 (pytest) and PYSEC-2026-2270 (dotenv).

The final CPU lock is hash-locked from official PyPI and audits with zero known findings. The official BFCL checker smoke test verifies a correct call, wrong argument, and malformed output under the overrides. This is compatibility evidence for our AST path, not a guarantee for unused agentic categories.

The CPU package's model registry also imports qwen-agent, whose import path required `soundfile` despite omitting that dependency in the resolved base metadata. We added an explicit `soundfile==0.13.1` pin, regenerated hashes, and reran the clean audit and checker smoke test. This changes no correctness rules.

## GPU setuptools exception explicitly authorized by the user

vLLM 0.32.0 constrains setuptools below 81 on Python 3.12. The resolver selects 80.10.2. Its audit has three entries representing two distinct advisories:

- [GHSA-xmj3-9gf7-h52w](https://github.com/advisories/GHSA-xmj3-9gf7-h52w): Windows path escape while setuptools' legacy wheel installer processes attacker-controlled `namespace_packages.txt`. It requires Windows and that installation path. Our worker is Linux, installs frozen hash-verified wheels from PyPI using pip, and never feeds generated outputs or URLs into an installer. This documented attack path is absent.
- [GHSA-h35f-9h28-mq5c](https://github.com/advisories/GHSA-h35f-9h28-mq5c) / PYSEC-2026-3447 / CVE-2026-59890: Unicode-normalization mismatch when creating a source distribution on macOS can include excluded files. The Linux worker does not create source distributions and receives no `.env` file. This documented attack path is absent.

The complete listed fix 84.1.0 was uploaded 2026-10-19, only eight days before this review. It fails the requested 14-day cooldown and conflicts with vLLM's constraint. We prepared and audited a candidate override but did not install it. The user directed retaining supported setuptools for an install-time-only advisory after checking applicability. Consequently the final lock preserves the constraint and the audit explicitly suppresses only these two advisory IDs. A successful audit here means **zero unaccepted findings**, not zero published vulnerabilities. Raw advisory evidence is retained in `results/security/`; no broad ignore or unpinned upgrade is allowed. If the OS, installer path, package source, or source-build behavior changes, reconsider this exception.

## Runtime initialization failure and prepared image correction

The first actual L4 worker failed before its smoke test: Triton's runtime driver helper could not find a C compiler in the minimal Python image. No benchmark generations were collected. The failure does not establish a model, CUDA, or batch-invariance defect; the immediate observed cause is a missing host compiler.

The correction installs official Debian trixie `build-essential=12.12` alongside `libnuma1=2.0.19-1`. It compiles a tiny C source including Python.h during the CPU image build, before any GPU allocation. [Official Debian package](https://packages.debian.org/trixie/build-essential). This permits compilation of the trusted installed Triton runtime helper. It preserves pip's wheel-only, hash-verified installation policy and does not invoke the affected setuptools paths. Pip-audit does not audit Debian OS packages. At the first failure, the correction was prepared locally and compute stopped pending approval. The later validation is recorded below.

**October 27 retry:** the corrected image was built, the CPU compiler/headers preflight passed, and the actual image audit completed with only the same documented exceptions. Before the first L4 smoke submission could be accepted, Modal reported a local-client disconnect and `ConflictError: The app is stopped or disabled`. Zero function calls and zero GPU containers are recorded for that retry. GPU validation was still pending at that point. Compute stopped until the user's subsequent approval. The build log and preflight/audit evidence are retained under `results/pilot-20261027T144048Z/`.

**October 28 subsequent approval and validation:** app listing was empty and the existing token authenticated, with token values suppressed. A fresh client and a detached, bounded single call used the same compiler-equipped image plus a fresh CPU preflight/audit layer. Both passed. Modal selected NVIDIA A10 from the approved L4/A10 priority list. Five initial smoke requests and all four model/arm stages passed on that GPU; one successful job and one GPU container are recorded. No connection retry or job resubmission was needed. The accepted setuptools exceptions are unchanged. No L4 runtime validation is claimed. The evalnoise app is stopped, and no unrelated app was modified. Evidence: `results/pilot-20261028T050156Z/`.

## Reproducibility and audit commands

The approved remaining-five continuation passed the same compiler preflight and image audit. OCI pinning was rejected before submission, so the serving request remains Modal's `A10` tier with automatic provider selection. All five new models share one exact UUID; the preserved first model retains its earlier device. Exact NVIDIA A10/A10G names are retained in results, and cross-device anchor comparisons are identified. The server controller enforces allocation and budget deadlines independently of the laptop. Local interruption leaves the detached job running. Its volume contains only evaluation artifacts, is separate from model caches and credentials, and is deleted only after verified local downloads.

The October 28 full-study launch uses the same locks and documented exceptions. Fresh local, BFCL, and GPU-lock audits passed before launch. The updated image passed C/Python-header compilation and an audit of its installed packages before A10 allocation. Model revisions, official license/configuration files, and hashes for the selected six checkpoints are in `experiments/full-models.json` and `results/metadata/full-model-sources.json`. The gated Llama configuration was downloaded successfully using the existing Hugging Face credential store. Only that token is passed through an ephemeral Modal secret, never through serialized payloads or result metadata. No credential was copied to the repository.

The first full-study call stopped before inference because a device-name guard rejected Modal's A10-tier `NVIDIA A10G` name. The corrected guard accepts only A10-tier names. After the later infrastructure interruption, the approved continuation keeps the remaining five models on one exact GPU UUID and preserves the first model's earlier A10 outputs. Every model's arms share its assigned device. This changes no dependency, checkpoint, prompt, or correctness rule.

Before Llama started, a tokenization check found that vLLM's completion entry point adds special tokens by default, while Llama's rendered chat already contains its beginning-of-sequence token. The correction passes `add_special_tokens=False` for Llama's rendered benchmark and warmup prompts. All 500 prompts for each other model produced identical token IDs with either setting. The owned running container received the corrected trusted worker source before any Llama process started, without a job restart or dependency change. Original and corrected source, an installation receipt, and hashes are archived under `results/study-20261028T065939Z/continuation-checkpoints/runtime-fixes/tokenization/`. The report validator requires the corrected setting in every Llama arm's metadata. See `results/metadata/special-token-preflight.json` and the corresponding decision in DECISIONS.md.

`uv.lock` contains local package hashes. The separate `experiments/bfcl.lock` and `experiments/gpu.lock` are requirements files with SHA256 hashes, resolved only at `https://pypi.org/simple`. Use `UV_HTTP_TIMEOUT=120` and a workspace-local cache. The GPU target platform must match its Linux image; wheel-only resolution prevents hidden source builds. Never enable an unofficial package mirror to work around a timeout.

```sh
UV_CACHE_DIR=.uv-cache UV_HTTP_TIMEOUT=120 uv sync --frozen --group modal
.venv/bin/pip-audit --cache-dir .uv-cache/pip-audit --format json --output results/audit-local.json
.venv/bin/pip-audit -r experiments/bfcl.lock --no-deps --disable-pip --cache-dir .uv-cache/pip-audit --format json --output results/audit-bfcl.json
.venv/bin/pip-audit -r experiments/gpu.lock --no-deps --disable-pip --cache-dir .uv-cache/pip-audit --ignore-vuln PYSEC-2026-3447 --ignore-vuln GHSA-xmj3-9gf7-h52w --format json --output results/audit-gpu.json
```

Lock audits inspect the fully resolved pins, without installing Linux packages on macOS. The Modal image also audits its actual Python environment before GPU use, using only the same two approved ignores. Keep local editable project skips distinct from dependency findings. Audit results are time-specific database checks, not proof of absence of all vulnerabilities.

## Completed study and cleanup

All six model artifacts retain compiler-preflight, installed-image audit, package, driver, GPU, prompt, and timing metadata. The pinned environments and advisory exceptions were unchanged during the continuation. The Llama correction changed only trusted worker tokenization code before that model started. No additional package or model-supplied code was installed.

The detached job completed without a GPU retry. One temporary local volume-read error required reconnecting the observer to the existing call; it did not restart inference. Every downloaded checkpoint matched its committed SHA256. The temporary results volume was then deleted. All owned study apps are stopped with zero running containers, and qunti-check was not modified. See the final study receipt and `results/metadata/verification.json`. Ruff excludes dependency caches, the separate BFCL environment, distribution files, and archived research sources; checks do not rewrite those pinned dependencies or source snapshots.

## Authorized L4 follow-up

The focused L4 replication reuses the same pinned image dependencies, frozen checkpoint revisions, hash locks, and narrowly accepted setuptools exceptions. Fresh local and BFCL audits have zero findings. The new image `im-obEKh2U42ueQJsLV8NzYcF` passed C/Python-header compilation and its installed-package audit before GPU submission, with the same three ignored aliases and zero unaccepted findings. No dependency was added or upgraded. Trusted worker changes add opt-in greedy-only flags and an explicit L4 device allowlist; A10 defaults remain intact. Source snapshots and the original A10 verification are preserved in the follow-up session. Credentials continue to use the existing stores and ephemeral Modal secret; values are never written into results.

The first L4 was preempted after two complete, SHA256-verified models. The continuation image `im-3NIzpicUFwLOMpbHR4GyH2` passed a fresh compiler preflight and installed-package audit with the same accepted exceptions. It adds a persistent execution claim, committed before inference, so platform restarts cannot regenerate completed work. The CPU controller restores saved GPU call IDs and has non-preemptible CPU allocation; this does not make the GPU non-preemptible. A local integration test invokes the actual GPU function body twice with simulated model execution and verifies that only the first invocation generates outputs and checkpoint bytes remain unchanged. All 47 local tests passed. Inference dependencies and model revisions are unchanged.

The completed L4 follow-up passed all eight model/arm five-request smoke gates and scored 12,000 outcomes with the unchanged official checker. Both volumes were deleted only after SHA256-verified downloads; all owned apps are stopped and reservations released. The two preserved primary checkpoints and all 6,000 scored primary rows match byte for byte. Final source/result hashes and A10 preservation checks are recorded in results/metadata/verification-l4.json.

## Editorial merge and workspace rename

The merged article and report use only saved summaries. No inference, scoring, Modal request, dependency upgrade, or paid compute is needed. The project directory is renamed to leaderboard-noise while the package and CLI remain evalnoise. Virtual-environment entry points and editable-install paths are rebased to the new directory; package versions and all hash lockfiles are unchanged. Current verification is recorded in results/metadata/verification-merged.json. Earlier verification manifests and byte-preserved document snapshots remain the historical record.

## Local paper build and release packaging

This manuscript uses frozen artifacts only. The original runtime, GPU, and BFCL locks remain unchanged. The official Tectonic 0.17.0 macOS ARM binary is verified against the GitHub release SHA256, and the TeX bundle URL is versioned. Its local compiler cache is outside the release. `paper/toolchain.json` records this document toolchain separately from inference.

Python packaging uses `paper/build-requirements.lock`, a hash-locked official-PyPI environment with zero known findings in `paper/build-audit.json`. Package license metadata includes the original MIT text plus BFCL Apache-2.0 text and attribution. Executed-source copies are byte-preserved and have both per-file checksums and process-level attestation labels. The release packager requires these files and rejects cache, credential, and weight paths. It does not create remote tags or releases. Audit/publication approval remains pending.
