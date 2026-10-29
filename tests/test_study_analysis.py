import importlib.util
from pathlib import Path

import numpy as np
import pytest


path = Path(__file__).parents[1] / "scripts/study_analysis.py"
spec = importlib.util.spec_from_file_location("study_analysis_test", path)
analysis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analysis)


def test_wilson_keeps_uncertainty_at_zero_events():
    lo, hi = analysis.wilson(0, 500)
    assert lo == pytest.approx(0, abs=1e-12)
    assert 0.007 < hi < 0.008


def test_paired_batch_flip_matches_enumerable_two_item_example():
    result = analysis.flip_summary([[1, -1], [-1, 1]], seed=10, resamples=5000, outer=40, inner=100)
    assert result["estimate"] == pytest.approx(0.5, abs=0.025)
    assert result["any_tie_fraction"] == pytest.approx(0.5, abs=0.025)
    assert not result["observed_strict_flip"]
    assert result["ci95"][0] <= result["estimate"] + 0.05 <= result["ci95"][1]


def test_identical_batch_outcomes_cannot_flip_on_empirical_support():
    result = analysis.flip_summary(
        [[1, 1, 1], [-1, -1, -1], [0, 0, 0]], seed=1, outer=40, inner=100
    )
    assert result["estimate"] == 0
    assert result["ci95"] == [0, 0]
    assert result["mc_wilson95"][1] > 0
    assert result["collapsed_outer_interval"]


def test_sampling_flip_does_not_assign_direction_to_observed_tie():
    result = analysis.flip_summary(np.array([1, -1]), seed=1, kind="sampling")
    assert result["estimate"] is None
