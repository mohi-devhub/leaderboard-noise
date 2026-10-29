"""Release integrity: mandatory licenses, exact source bytes, and archive checksums."""

import hashlib
import json
from pathlib import Path
import subprocess
import tarfile

import pytest

from scripts.package_release import REQUIRED, package, validate_inputs


def fixture_tree(tmp_path):
    for name in REQUIRED:
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("test fixture only\n")
    (tmp_path / "provenance/manifest.json").write_text(json.dumps({"files": []}))
    return [tmp_path / n for n in REQUIRED]


def test_packager_requires_bfcl_notice_and_original_license(tmp_path):
    files = fixture_tree(tmp_path)
    for missing in ("LICENSE", "third_party/BFCL/LICENSE", "third_party/BFCL/NOTICE"):
        with pytest.raises(ValueError, match="Missing mandatory"):
            validate_inputs(tmp_path, [p for p in files if p != tmp_path / missing])


def test_packager_rejects_modified_provenance(tmp_path):
    files = fixture_tree(tmp_path)
    snapshot = tmp_path / "provenance/worker.py"
    snapshot.write_text("modified source")
    (tmp_path / "provenance/manifest.json").write_text(
        json.dumps(
            {
                "files": [
                    {
                        "path": "provenance/worker.py",
                        "sha256": hashlib.sha256(b"original source").hexdigest(),
                    }
                ]
            }
        )
    )
    with pytest.raises(ValueError, match="modified executed source"):
        validate_inputs(tmp_path, files + [snapshot])


def test_release_archive_contains_licenses_and_checkable_checksums(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    fixture_tree(root)
    for args in (
        ["init", "-b", "main"],
        ["config", "user.name", "Test"],
        ["config", "user.email", "test@example.invalid"],
        ["add", "."],
        ["commit", "-m", "test fixture"],
    ):
        subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)
    archive = package(root, tmp_path / "output")
    with tarfile.open(archive) as tar:
        prefix = "leaderboard-noise-v0.1.0-paper/"
        names = {m.name[len(prefix) :] for m in tar.getmembers()}
        assert REQUIRED <= names
        sums = tar.extractfile(prefix + "SHA256SUMS").read().decode()
        for line in sums.splitlines():
            expected, name = line.split("  ", 1)
            assert hashlib.sha256(tar.extractfile(prefix + name).read()).hexdigest() == expected
    assert (
        archive.with_name(archive.name + ".sha256").read_text().split()[0]
        == hashlib.sha256(archive.read_bytes()).hexdigest()
    )


def test_shipped_provenance_matches_recorded_hashes():
    manifest = json.loads(Path("provenance/manifest.json").read_text())
    assert manifest["files"] and manifest["process_mapping"]
    for item in manifest["files"]:
        assert hashlib.sha256(Path(item["path"]).read_bytes()).hexdigest() == item["sha256"]
    assert any(
        row["attestation"] == "launch_only_no_runtime_self_hash"
        for row in manifest["process_mapping"]
    )
    assert any(row["attestation"] == "runtime_self_hash" for row in manifest["process_mapping"])


def test_packager_rejects_symlinks_and_unsafe_tags(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    files = fixture_tree(root)
    external = tmp_path / "external.txt"
    external.write_text("external test fixture")
    linked = root / "linked.txt"
    linked.symlink_to(external)
    with pytest.raises(ValueError, match="symlink"):
        validate_inputs(root, files + [linked])
    with pytest.raises(ValueError, match="Unsafe release tag"):
        package(root, tmp_path / "output", tag="../escape")
