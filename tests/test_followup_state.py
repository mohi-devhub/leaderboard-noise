import ast
import copy
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from followup_state import begin_once


def test_replay_preserves_checkpoints_without_starting_again(tmp_path):
    claim = {"session": "test-session", "started_at": "test-time"}
    assert begin_once(tmp_path, claim) is None
    checkpoint = {"model": "model-a", "status": "complete", "sha256": "test-hash"}
    (tmp_path / "progress.json").write_text(json.dumps({"models": [checkpoint]}))
    result = begin_once(tmp_path, claim)
    assert result["status"] == "preemption_restart_blocked"
    assert result["models"] == [checkpoint]
    assert json.loads((tmp_path / "execution-claim.json").read_text()) == claim


def test_completed_manifest_is_returned_unchanged_on_replay(tmp_path):
    claim = {"session": "test-session"}
    assert begin_once(tmp_path, claim) is None
    complete = {"status": "complete", "models": [{"model": "model-a"}]}
    (tmp_path / "manifest.json").write_text(json.dumps(complete))
    assert begin_once(tmp_path, claim) == complete


def test_other_session_cannot_reuse_the_execution_claim(tmp_path):
    assert begin_once(tmp_path, {"session": "first"}) is None
    with pytest.raises(RuntimeError, match="another session"):
        begin_once(tmp_path, {"session": "second"})


def test_actual_gpu_function_does_not_replay_completed_models(monkeypatch, tmp_path):
    import pathlib
    import study_model_job
    import subprocess

    source = Path(__file__).parents[1] / "scripts/run_l4_followup.py"
    tree = ast.parse(source.read_text())
    definition = copy.deepcopy(
        next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "gpu_job"
        )
    )
    definition.decorator_list = []
    namespace = {"volume": SimpleNamespace(commit=lambda: None)}
    exec(compile(ast.Module(body=[definition], type_ignores=[]), str(source), "exec"), namespace)
    generated = []

    def execute(payload):
        generated.append(payload["model"]["id"])
        return {"status": "complete", "remote_seconds": 0, "model": payload["model"]["id"]}

    monkeypatch.setattr(study_model_job, "execute_model", execute)
    monkeypatch.setattr(subprocess, "check_output", lambda *a, **k: "synthetic-uuid")
    monkeypatch.setitem(
        sys.modules,
        "torch",
        SimpleNamespace(cuda=SimpleNamespace(get_device_name=lambda: "NVIDIA L4")),
    )
    real_path = pathlib.Path
    monkeypatch.setattr(
        pathlib, "Path", lambda value: tmp_path if value == "/artifacts" else real_path(value)
    )
    payload = {
        "session": "synthetic-unit-test",
        "models": [{"id": "fixture-a"}, {"id": "fixture-b"}],
        "items": [],
        "config": {},
        "plan": {
            "execution_limit_seconds": 60,
            "non_gpu_allowance_usd": 0,
            "gpu_resource_hourly_usd": 1,
            "controller_resource_hourly_usd": 0.1,
            "effective_followup_cap_usd": 10,
            "models": [{"execution_limit_seconds": 10}] * 2,
        },
    }
    first = namespace["gpu_job"](payload)
    checkpoint = (tmp_path / "fixture-a.json").read_bytes()
    second = namespace["gpu_job"](payload)
    assert first == second
    assert generated == ["fixture-a", "fixture-b"]
    assert (tmp_path / "fixture-a.json").read_bytes() == checkpoint
