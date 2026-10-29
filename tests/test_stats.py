from itertools import combinations
import json

import numpy as np
import pytest

from evalnoise.cli import greedy, main
from evalnoise.data import load
from evalnoise.stats import analyze, pass_at_k, planning


def test_pass_k_matches_exhaustive_without_replacement():
    for n in range(1, 9):
        for c in range(n + 1):
            for k in range(1, n + 1):
                draws = list(combinations(range(n), k))
                exact = sum(any(i < c for i in draw) for draw in draws) / len(draws)
                assert pass_at_k(n, c, k) == pytest.approx(exact)


def test_pairing_cancels_identical_item_effects():
    row = [np.array([v] * 10) for v in [0, 1, 0, 1, 1]]
    report = analyze(["A", "B"], list("abcde"), [row, row], ks=[1], resamples=100)
    pairs = report["metrics"]["pass@1"]["items"]["pairwise"]
    assert pairs[0]["ci"] == [0, 0]
    assert pairs[0]["p_tie"] == 1
    assert pairs[0]["rank_flip_frequency"] is None
    assert pairs[0]["planning"]["status"] == "unidentified_zero_empirical_variance"
    assert report["metrics"]["pass@1"]["items"]["models"]["A"]["ci"][0] < 0.6


def test_sampling_uncertainty_survives_equal_item_means():
    row = [np.array([0, 1] * 5, dtype=float) for _ in range(20)]
    r = analyze(["A", "B"], list(range(20)), [row, row], ks=[1], resamples=1000)
    metric = r["metrics"]["pass@1"]
    assert metric["items"]["models"]["A"]["ci"] == [0.5, 0.5]
    assert metric["sampling"]["models"]["A"]["bootstrap_se"] > 0
    plan = metric["items"]["pairwise"][0]["planning"]
    assert plan["between_variance_clipped"]
    assert plan["mdd_current_design"] > 0


def test_sampling_se_matches_conditional_bernoulli_variance():
    row = [np.array([0] * 7 + [1] * 3) for _ in range(30)]
    r = analyze(["A"], list(range(30)), [row], ks=[1], resamples=5000)
    se = r["metrics"]["pass@1"]["sampling"]["models"]["A"]["bootstrap_se"]
    assert se == pytest.approx(np.sqrt(0.3 * 0.7 / 300), rel=0.05)


def test_rank_flips_obey_observed_direction_and_probability_partition():
    a = [np.array([1] * 10), np.array([1] * 10), np.array([0] * 10)]
    b = [np.array([0] * 10), np.array([0] * 10), np.array([1] * 10)]
    r = analyze(["A", "B"], list("abc"), [a, b], ks=[1], resamples=2000)
    p = r["metrics"]["pass@1"]["items"]["pairwise"][0]
    assert p["rank_flip_frequency"] == p["p_b_beats_a"]
    assert p["p_a_beats_b"] + p["p_tie"] + p["p_b_beats_a"] == pytest.approx(1)
    assert 0 < p["rank_flip_frequency"] < 0.5


def test_planning_sqrt_n_and_more_samples():
    rng = np.random.default_rng(8)
    a = [rng.binomial(1, p, 10) for p in np.linspace(0.1, 0.9, 200)]
    b = [rng.binomial(1, 0.5, 10) for _ in a]
    p = planning(a, b, 0.05, 0.05, 0.8, [1, 10, 20])
    assert p["grid"][0]["mdd"] > p["grid"][-1]["mdd"]
    assert p["grid"][0]["items_for_target_gap"] > p["grid"][-1]["items_for_target_gap"]
    q = planning(a * 4, b * 4, 0.05, 0.05, 0.8, [10])
    assert q["mdd_current_design"] == pytest.approx(p["mdd_current_design"] / 2, rel=0.01)


def write(tmp_path, rows):
    path = tmp_path / "rows.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return path


def test_field_mapping_and_item_weighting(tmp_path):
    rows = [
        {"m": "A", "x": item, "s": s, "v": {"ok": value}}
        for item, samples in [("x", [0, 0, 0]), ("y", [1])]
        for s, value in enumerate(samples)
    ]
    _, _, data = load(write(tmp_path, rows), "m", "x", "v.ok", "s")
    assert np.mean([x.mean() for x in data[0]]) == 0.5


@pytest.mark.parametrize(
    "rows, error",
    [
        (
            [
                {"model": "A", "item_id": "x", "successes": [0]},
                {"model": "A", "item_id": "x", "successes": [1]},
            ],
            "duplicate",
        ),
        ([{"model": "A", "item_id": "x", "successes": [0.5]}], "binary"),
        (
            [
                {"model": "A", "item_id": "x", "successes": [1], "condition": "one"},
                {"model": "A", "item_id": "y", "successes": [0], "condition": "two"},
            ],
            "mixed",
        ),
        (
            [
                {"model": "A", "item_id": "x", "successes": [1]},
                {"model": "A", "item_id": "y", "successes": [0]},
                {"model": "B", "item_id": "z", "successes": [0]},
            ],
            "identical item sets",
        ),
    ],
)
def test_reject_bad_inputs(tmp_path, rows, error):
    with pytest.raises(ValueError, match=error):
        load(write(tmp_path, rows))


def test_reproducibility_and_cli(tmp_path, capsys):
    rows = [{"model": m, "item_id": i, "successes": [0, 1]} for m in ["A", "B"] for i in ["x", "y"]]
    path = write(tmp_path, rows)
    args = ["analyze", str(path), "--resamples", "100", "--format", "json"]
    assert main(args) == 0
    first = capsys.readouterr().out
    assert main(args) == 0
    assert capsys.readouterr().out == first
    assert main(args + ["--k", "3"]) == 2


def test_greedy_exact_comparison_and_missing_runs():
    rows = [
        {
            "model": "A",
            "item_id": "x",
            "run_id": i,
            "temperature": 0,
            "output": "foo" if i < 2 else "foo ",
            "passed": True,
        }
        for i in range(3)
    ]
    result = greedy(rows)["models"]["A"]
    assert result["changed_fraction"] == 1
    assert result["score_changed_fraction"] == 0
    with pytest.raises(ValueError, match="three"):
        greedy(rows[:2])
