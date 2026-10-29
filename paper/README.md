# Standalone paper

`main.tex` is the manuscript; `main.pdf` is its compiled output. Tables, numeric macros, and grayscale vector quantitative figures are generated from saved artifacts by `scripts/paper_assets.py`. `overview.tex` is a vector TikZ method diagram. No build command performs inference, scoring, or resampling.

Run from the project root with the existing uv environment:

```sh
.venv/bin/python scripts/build_paper.py --tectonic /path/to/tectonic
```

The official Tectonic binary and its SHA256 are recorded in `toolchain.json`; cached TeX resources are not redistributed. A standard LaTeX installation with BibTeX can also compile the source. `artifact-map.json` maps generated numbers and tables to frozen inputs. `references-verified.json` records primary-source citation checks. All intervals are exploratory and unadjusted.

The intended local release-candidate tag is `v0.1.0-paper`. The archive, local tag, and manuscript await a fresh-session audit and approval. No public GitHub release or remote tag is published by the build or release packager.

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
