"""Regression for the observed stop/already-stopped race and explicit cleanup scope."""

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


def test_already_stopped_race_preserves_unrelated_app(monkeypatch, tmp_path):
    pytest.importorskip("modal")
    path = Path(__file__).parents[1] / "scripts" / "run_pilot.py"
    spec = importlib.util.spec_from_file_location("pilot_cleanup_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original = [{"app_id": "ours", "state": "ephemeral"}, {"app_id": "other", "state": "ephemeral"}]
    final = [{"app_id": "ours", "state": "stopped"}, {"app_id": "other", "state": "ephemeral"}]
    responses = iter([original, final])
    monkeypatch.setattr(module, "command_json", lambda *args: next(responses))
    stopped = []

    def stop(args, **kwargs):
        stopped.append(args)
        return SimpleNamespace(returncode=1, stdout="App is already stopped.", stderr="")

    monkeypatch.setattr(module.subprocess, "run", stop)
    output = tmp_path / "shutdown.json"
    module.shutdown(output, own_app_id="ours", stop_all=False)
    assert len(stopped) == 1 and "ours" in stopped[0] and "other" not in stopped[0]
    assert json.loads(output.read_text())["apps"][-1]["state"] == "ephemeral"


def test_pilot_payload_keeps_seed_index_and_excludes_answers(tmp_path):
    pytest.importorskip("modal")
    path = Path(__file__).parents[1] / "scripts" / "run_pilot.py"
    spec = importlib.util.spec_from_file_location("pilot_payload_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    item_path = tmp_path / "items.jsonl"
    item_path.write_text(
        json.dumps(
            {
                "item_id": "selected",
                "messages": [],
                "messages_sha256": "hash",
                "ground_truth": "must not reach GPU",
            }
        )
        + "\n"
    )
    items = module.pilot_items(
        item_path, {"full_ids": ["other", "selected"], "pilot_ids": ["selected"]}
    )
    assert items[0]["seed_index"] == 1
    assert "ground_truth" not in items[0]
