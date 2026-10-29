"""Protect the explicit GPU/batch winner claims in the published documents."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from scripts.write_study_article import A10, L4, LEAD, load_study, render, winner_rows


@pytest.fixture(scope="module")
def study():
    return load_study(A10, L4)


def test_default_winners_name_each_gpu_and_batch(study):
    rows = winner_rows(study)
    assert len(rows) == 12
    target = {(r["gpu"], r["batch"]): r for r in rows if r["a"].startswith("meta-llama/")}
    expected = {
        ("A10", 1): (457, 458, "Qwen3-4B-Instruct-2507"),
        ("A10", 8): (457, 457, "Tie"),
        ("A10", 32): (457, 456, "Llama-3.2-3B-Instruct"),
        ("L4", 1): (458, 457, "Llama-3.2-3B-Instruct"),
        ("L4", 8): (457, 457, "Tie"),
        ("L4", 32): (458, 459, "Qwen3-4B-Instruct-2507"),
    }
    for key, values in expected.items():
        assert tuple(target[key][k] for k in ("a_correct", "b_correct", "higher_rank")) == values
    assert all(r["higher_rank"] == "Qwen3-1.7B" for r in rows if r["a"].startswith("Qwen/"))


@pytest.mark.parametrize("full", [False, True])
def test_documents_show_winners_and_qualify_intervals_and_throughput(study, full):
    text = render(study, Path("results/REPORT.md"), full=full)
    assert "| A10 | 1 | 457 | 458 | Qwen3-4B-Instruct-2507 |" in text
    assert "| L4 | 1 | 458 | 457 | Llama-3.2-3B-Instruct |" in text
    assert "| A10 | 32 | 457 | 456 | Llama-3.2-3B-Instruct |" in text
    assert "| L4 | 32 | 458 | 459 | Qwen3-4B-Instruct-2507 |" in text
    assert (
        "All confidence intervals in this article and the combined report are exploratory" in text
    )
    assert "L4 has no repeated throughput study" in text
    assert "not confidence intervals" in text
    assert "70,800 scored outputs" in text
    assert "one and zero" in text


def test_local_generator_writes_both_documents_without_changing_inputs(tmp_path, study):
    article = tmp_path / "STUDY.md"
    report = tmp_path / "REPORT.md"
    manifest = tmp_path / "sources.json"
    article.write_text(f"# Study\n\n{LEAD}\n\n<!-- results:start -->\n<!-- results:end -->\n")
    before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in study["sources"].values()}
    subprocess.run(
        [
            sys.executable,
            "scripts/write_study_article.py",
            "--out",
            str(article),
            "--report",
            str(report),
            "--manifest",
            str(manifest),
        ],
        check=True,
        capture_output=True,
    )
    saved = json.loads(manifest.read_text())
    assert saved["new_model_runs"] == 0
    assert saved["sources_sha256"] == before
    for source, digest in before.items():
        assert hashlib.sha256(Path(source).read_bytes()).hexdigest() == digest
    for path in (article, report):
        assert LEAD in path.read_text()
        assert "Higher rank" in path.read_text()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == saved["outputs_sha256"][str(path)]
