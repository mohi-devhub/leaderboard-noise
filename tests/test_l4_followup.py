from datetime import datetime, timezone
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from run_l4_followup import residency_seconds


def test_completed_call_does_not_charge_for_client_waiting():
    calls = [{"started_at": "2026-10-28T00:00:00Z", "execution_time_seconds": 100}]
    stopped = datetime(2026, 10, 28, 1, tzinfo=timezone.utc)
    assert residency_seconds(calls, stopped, 300) == 402


def test_unfinished_call_uses_confirmed_stop_time():
    calls = [{"started_at": "2026-10-28T00:00:00Z", "execution_time_seconds": None}]
    stopped = datetime(2026, 10, 28, 1, tzinfo=timezone.utc)
    assert residency_seconds(calls, stopped, 300) == 3900


def test_observed_startup_replaces_the_reserved_startup_allowance():
    calls = [
        {
            "started_at": "2026-10-28T00:00:00Z",
            "execution_time_seconds": 100,
            "startup_time_seconds": 7,
        }
    ]
    stopped = datetime(2026, 10, 28, 1, tzinfo=timezone.utc)
    assert residency_seconds(calls, stopped, 300) == 109


def test_more_than_one_job_is_rejected():
    stopped = datetime(2026, 10, 28, 1, tzinfo=timezone.utc)
    with pytest.raises(RuntimeError, match="more than one call"):
        residency_seconds([{}, {}], stopped, 0)
