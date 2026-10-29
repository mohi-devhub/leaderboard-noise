from contextlib import nullcontext
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


@pytest.fixture
def download_module(monkeypatch):
    scripts = Path(__file__).parents[1] / "scripts"
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location("remaining_test", scripts / "run_remaining.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "fresh_client", lambda: nullcontext("fresh-test-client"))
    return module


def fixture_artifact(tmp_path, name="remaining-model.json", sha=None):
    data = b'{"synthetic_test_fixture":true}'
    (tmp_path / "remaining-resources.json").write_text(
        json.dumps({"volume_name": "evalnoise-test-owned", "owned_by": "evalnoise"})
    )
    manifest = {
        "status": "complete",
        "models": [{"file": name, "sha256": sha or hashlib.sha256(data).hexdigest()}],
    }
    (tmp_path / "remaining-job-result.json").write_text(json.dumps(manifest))
    return data


def test_verified_download_deletes_only_owned_volume_and_is_repeatable(
    download_module, monkeypatch, tmp_path
):
    data = fixture_artifact(tmp_path)

    class Volume:
        def read_file(self, path):
            yield data[:10]
            yield data[10:]

    monkeypatch.setattr(download_module.modal.Volume, "from_name", lambda *a, **k: Volume())
    deleted = []
    monkeypatch.setattr(
        type(download_module.modal.Volume.objects),
        "delete",
        lambda self, name, **kwargs: deleted.append(name),
    )
    download_module.download_results(tmp_path)
    assert (tmp_path / "remaining-model.json").read_bytes() == data
    assert deleted == ["evalnoise-test-owned"]
    download_module.download_results(tmp_path)
    assert deleted == ["evalnoise-test-owned"]


def test_checksum_failure_preserves_remote_results(download_module, monkeypatch, tmp_path):
    data = fixture_artifact(tmp_path, sha="wrong-sha")

    class Volume:
        def read_file(self, path):
            yield data

    monkeypatch.setattr(download_module.modal.Volume, "from_name", lambda *a, **k: Volume())
    monkeypatch.setattr(
        type(download_module.modal.Volume.objects),
        "delete",
        lambda *a, **k: pytest.fail("must retain volume"),
    )
    with pytest.raises(RuntimeError, match="hash mismatch"):
        download_module.download_results(tmp_path)
    assert not (tmp_path / "remaining-model.json").exists()


def test_completed_model_cannot_be_replaced(download_module, monkeypatch, tmp_path):
    fixture_artifact(tmp_path, name="Qwen2.5-1.5B-Instruct.json")
    monkeypatch.setattr(download_module.modal.Volume, "from_name", lambda *a, **k: None)
    with pytest.raises(ValueError, match="completed model"):
        download_module.download_results(tmp_path)


def test_local_disconnect_never_stops_detached_job(download_module, monkeypatch, tmp_path):
    monkeypatch.setattr(
        download_module,
        "reconcile_stopped",
        lambda *a: pytest.fail("active remote job must survive"),
    )
    record = {"app_id": "owned-app", "reserved_usd": 9.5}
    ledger = {"entries": [record]}
    download_module.finalize_local_wait(
        tmp_path, record, ledger, tmp_path / "ledger.json", {}, None
    )
    saved = json.loads((tmp_path / "ledger.json").read_text())["entries"][0]
    assert saved["reserved_usd"] == 9.5
    assert saved["status"] == "remaining_detached_running_or_needs_recovery"


def test_terminal_remote_result_allows_cleanup(download_module, monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(download_module, "reconcile_stopped", lambda *a: calls.append(a))
    result = {"status": "complete"}
    record = {"app_id": "owned-app"}
    download_module.finalize_local_wait(tmp_path, record, {}, tmp_path / "ledger.json", {}, result)
    assert len(calls) == 1
    assert calls[0][1] is record
    assert calls[0][-1] is result
