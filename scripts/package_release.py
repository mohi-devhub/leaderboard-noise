"""Create a local release archive with both licenses, provenance, data and checksums.

This script never creates a remote tag or GitHub release, and never invokes evaluation.
"""

import argparse
import gzip
import hashlib
import io
import json
import re
from pathlib import Path
import subprocess
import tarfile

TAG = "v0.1.0-paper"
REQUIRED = {
    "LICENSE",
    "third_party/BFCL/LICENSE",
    "third_party/BFCL/NOTICE",
    "paper/main.tex",
    "paper/main.pdf",
    "paper/references.bib",
    "paper/references-verified.json",
    "paper/artifact-map.json",
    "paper/toolchain.json",
    "provenance/manifest.json",
    "provenance/SHA256SUMS",
    "scripts/paper_assets.py",
    "scripts/collect_provenance.py",
    "src/evalnoise/cli.py",
    "experiments/subset.json",
    "experiments/bfcl-items.jsonl",
}
FORBIDDEN_PARTS = {
    ".git",
    ".venv",
    ".venv-bfcl",
    ".uv-cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "dist",
    "build",
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_inputs(root, paths):
    for p in paths:
        if p.is_symlink() or root.resolve() not in p.resolve().parents:
            raise ValueError("Release inputs must not be symlinks or escape the project root")
    names = {str(p.relative_to(root)) for p in paths}
    missing = REQUIRED - names
    if missing:
        raise ValueError("Missing mandatory release inputs: " + ", ".join(sorted(missing)))
    for name in names:
        p = Path(name)
        if p.is_absolute() or ".." in p.parts or any(x in FORBIDDEN_PARTS for x in p.parts):
            raise ValueError("Forbidden path: " + name)
        if (p.name.startswith(".env") and p.name != ".env.example") or p.suffix in {
            ".safetensors",
            ".pt",
            ".pth",
            ".bin",
        }:
            raise ValueError("Credential/weight path forbidden: " + name)
    for record in json.loads((root / "provenance/manifest.json").read_text())["files"]:
        path = root / record["path"]
        if record["path"] not in names or sha(path) != record["sha256"]:
            raise ValueError("Missing or modified executed source: " + record["path"])
    return names


def package(root, out, tag=TAG, distributions=None):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,100}", tag) or ".." in tag:
        raise ValueError("Unsafe release tag")
    root = root.resolve()
    out.mkdir(parents=True, exist_ok=True)
    listing = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    files = [
        root / p
        for p in set(listing.split("\0"))
        if p and (root / p).is_file() and not p.startswith("releases/")
    ]
    validate_inputs(root, files)
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()
    payload = {str(p.relative_to(root)): p.read_bytes() for p in files}
    if distributions:
        for p in sorted(distributions.iterdir()):
            if p.suffix == ".whl" or p.name.endswith(".tar.gz"):
                payload["distributions/" + p.name] = p.read_bytes()
    release = {
        "tag": tag,
        "tag_status": "local release candidate; no remote publication by this script",
        "source_commit": commit,
        "public_repository": "https://github.com/mohi-devhub/leaderboard-noise",
        "fresh_session_audit": "pending",
        "new_inference_or_resampling": False,
        "licenses": ["LICENSE", "third_party/BFCL/LICENSE", "third_party/BFCL/NOTICE"],
        "file_count_without_generated_manifests": len(payload),
    }
    payload["RELEASE.json"] = (json.dumps(release, indent=2) + "\n").encode()
    sums = "".join(
        hashlib.sha256(v).hexdigest() + "  " + k + "\n" for k, v in sorted(payload.items())
    )
    payload["SHA256SUMS"] = sums.encode()
    target = out / f"leaderboard-noise-{tag}.tar.gz"
    with target.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", filename="", mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w") as archive:
                for name, body in sorted(payload.items()):
                    info = tarfile.TarInfo("leaderboard-noise-" + tag + "/" + name)
                    info.size = len(body)
                    info.mtime = 0
                    info.mode = 0o644
                    archive.addfile(info, io.BytesIO(body))
    (out / (target.name + ".sha256")).write_text(sha(target) + "  " + target.name + "\n")
    with tarfile.open(target) as archive:
        prefix = "leaderboard-noise-" + tag + "/"
        members = {x.name[len(prefix) :]: x for x in archive.getmembers() if x.isfile()}
        actual = archive.extractfile(members["SHA256SUMS"]).read().decode()
        for line in actual.splitlines():
            expected, name = line.split("  ", 1)
            if hashlib.sha256(archive.extractfile(members[name]).read()).hexdigest() != expected:
                raise ValueError("Archive checksum failure: " + name)
        if not REQUIRED <= set(members):
            raise ValueError("Mandatory files missing from archive")
    receipt = {
        "archive": str(target),
        "sha256": sha(target),
        "files": len(payload),
        "required_files_verified": sorted(REQUIRED),
        "all_internal_checksums_verified": True,
        "remote_tag_or_release_created": False,
        "source_commit": commit,
        "tag": tag,
    }
    (out / "package-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))
    return target


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, default=Path("."))
    p.add_argument("--out", type=Path, default=Path("releases"))
    p.add_argument("--tag", default=TAG)
    p.add_argument("--distributions", type=Path)
    a = p.parse_args()
    package(a.root, a.out, a.tag, a.distributions)
