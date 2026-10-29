"""Reattach to an existing call once; this module cannot submit jobs."""

from contextlib import contextmanager
import builtins

import modal
from grpclib.exceptions import GRPCError, StreamTerminatedError
from grpclib.const import Status


@contextmanager
def fresh_client():
    from modal.config import config
    from modal_proto import api_pb2

    # Use the configured credentials in memory; never serialize them into job inputs.
    if not config["token_id"] or not config["token_secret"]:
        raise modal.exception.AuthError("configured token credentials are required")
    with modal.Client(
        config["server_url"],
        api_pb2.CLIENT_TYPE_CLIENT,
        (config["token_id"], config["token_secret"]),
    ) as client:
        yield client


def is_connection_failure(exc):
    if isinstance(exc, (modal.exception.FunctionTimeoutError, modal.exception.RemoteError)):
        return False
    if isinstance(exc, GRPCError):
        return exc.status in {
            Status.UNAVAILABLE,
            Status.CANCELLED,
            Status.INTERNAL,
            Status.DEADLINE_EXCEEDED,
        }
    return isinstance(
        exc,
        (
            modal.exception.ConnectionError,
            modal.exception.ConflictError,
            builtins.ConnectionError,
            StreamTerminatedError,
        ),
    )


def wait_existing_call(call, timeout, record_reconnect):
    """A transport failure gets one fresh connection to the identical saved call ID."""
    try:
        return call.get(timeout=timeout)
    except Exception as exc:
        if not is_connection_failure(exc):
            raise
        call_id = call.object_id
        record_reconnect(call_id, type(exc).__name__)
        with fresh_client() as client:
            return modal.FunctionCall.from_id(call_id, client=client).get(timeout=timeout)
