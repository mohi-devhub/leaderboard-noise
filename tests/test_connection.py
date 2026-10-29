"""Connection recovery must never create another paid job."""

from contextlib import contextmanager
import importlib.util
from pathlib import Path

import pytest


def connection_module():
    pytest.importorskip("modal")
    spec = importlib.util.spec_from_file_location(
        "connection_test", Path(__file__).parents[1] / "scripts/modal_connection.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("second_failure", [False, True])
def test_connection_recovery_reattaches_once_to_same_id(monkeypatch, second_failure):
    module = connection_module()
    events = []

    class Original:
        object_id = "fc-existing"

        def get(self, timeout):
            events.append("first_get")
            raise ConnectionError("disconnected")

    class Reattached:
        def get(self, timeout):
            events.append("second_get")
            if second_failure:
                raise ConnectionError("still disconnected")
            return {"status": "complete"}

    @contextmanager
    def fresh():
        events.append("fresh_connection")
        yield "new-client"

    def from_id(call_id, client):
        assert call_id == "fc-existing" and client == "new-client"
        events.append("reattach_existing_id")
        return Reattached()

    monkeypatch.setattr(module, "fresh_client", fresh)
    monkeypatch.setattr(module.modal.FunctionCall, "from_id", from_id)

    def callback(call_id, error):
        events.append((call_id, error))

    if second_failure:
        with pytest.raises(ConnectionError, match="still disconnected"):
            module.wait_existing_call(Original(), 30, callback)
    else:
        assert module.wait_existing_call(Original(), 30, callback) == {"status": "complete"}
    assert events == [
        "first_get",
        ("fc-existing", "ConnectionError"),
        "fresh_connection",
        "reattach_existing_id",
        "second_get",
    ]


def test_execution_timeout_does_not_trigger_connection_retry():
    module = connection_module()
    assert not module.is_connection_failure(
        module.modal.exception.FunctionTimeoutError("job timed out")
    )
    assert not module.is_connection_failure(module.modal.exception.RemoteError("worker failed"))
