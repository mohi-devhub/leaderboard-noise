# Standalone paper

`main.tex` is the manuscript; `main.pdf` is its compiled output. Tables, numeric macros, and grayscale vector quantitative figures are generated from saved artifacts by `scripts/paper_assets.py`. `overview.tex` is a vector TikZ method diagram. No build command performs inference, scoring, or resampling.

Run from the project root with the existing uv environment:

```sh
.venv/bin/python scripts/build_paper.py --tectonic /path/to/tectonic
```

The official Tectonic binary and its SHA256 are recorded in `toolchain.json`; cached TeX resources are not redistributed. A standard LaTeX installation with BibTeX can also compile the source. `artifact-map.json` maps generated numbers and tables to frozen inputs. `references-verified.json` records primary-source citation checks. All intervals are exploratory and unadjusted.

The [v0.1.0-paper release](https://github.com/mohi-devhub/leaderboard-noise/releases/tag/v0.1.0-paper) contains the manuscript and reproducibility archive. The [pre-release audit](../AUDIT.md), [wording revision record](../docs/REVISION_SENTENCES.md), and [revision verification](revision-verification.json) document the corrections. The original `verification.json` and `results/combined-sources.json` preserve the pre-audit candidate record, including its original document digests. Only the current combined report has a wording-only change among the original frozen-manifest paths; all empirical artifacts remain unchanged. Build and packaging scripts do not publish releases.

Build the Python distributions using the separately hash-locked backend environment, then create the local research archive:

```sh
uv venv .venv-build --python 3.12
uv pip sync --python .venv-build/bin/python --require-hashes paper/build-requirements.lock
uv build --no-build-isolation --python .venv-build/bin/python --out-dir releases/distributions
.venv/bin/python scripts/package_release.py --distributions releases/distributions
cd releases
shasum -a 256 -c leaderboard-noise-v0.1.0-paper.tar.gz.sha256
```

After extraction, run `shasum -a 256 -c SHA256SUMS` from the archive root. The external checksum and internal per-file checksums detect mismatched bytes; they are not independent signatures.
