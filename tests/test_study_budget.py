import importlib.util
from pathlib import Path

import pytest


path = Path(__file__).parents[1] / "scripts/study_budget.py"
spec = importlib.util.spec_from_file_location("study_budget_test", path)
budget = importlib.util.module_from_spec(spec)
spec.loader.exec_module(budget)


def test_next_model_cannot_cross_project_or_batch_limit():
    budget.require_headroom(10.0, 2.0)
    with pytest.raises(ValueError, match="project total"):
        budget.require_headroom(10.01, 2.0)
    with pytest.raises(ValueError, match="approval threshold"):
        budget.require_headroom(0.0, 5.01)


def test_forecast_counts_full_eval_and_repeated_fixed_item_timing():
    pilot = {
        "arms": [
            {
                "metadata": {
                    "timings": [
                        {"run_id": "sampling", "elapsed_seconds": 10},
                        {"run_id": "serial", "elapsed_seconds": 20},
                    ]
                }
            }
        ]
    }
    result = budget.forecast_model(pilot, 2, n_items=500, timing_items=100, repetitions=3)
    assert result["forecast_seconds"] == 2 * (10 * 5 + 20 * 8) + 200
    assert result["execution_limit_seconds"] > result["forecast_seconds"]
    assert budget.resource_estimate(3600, 1.4172, 0.15) == pytest.approx(1.5672)
