"""Item-paired bootstrap and explicit conditional generation resampling."""

from itertools import combinations
import math
from statistics import NormalDist

import numpy as np


def pass_at_k(n, c, k):
    """Unbiased estimator under independent, identically distributed generations."""
    if not (isinstance(k, int) and 1 <= k <= n and 0 <= c <= n):
        raise ValueError("require 1 <= k <= n and 0 <= c <= n")
    if n - c < k:
        return 1.0
    return 1.0 - math.prod((n - c - j) / (n - j) for j in range(k))


def item_scores(samples, k):
    return np.array([pass_at_k(len(x), int(x.sum()), k) for x in samples])


def interval(x, confidence):
    tail = (1 - confidence) / 2
    return [float(v) for v in np.quantile(x, [tail, 1 - tail])]


def planning(a, b, gap, alpha, power, sample_grid):
    """Correct finite-repeat contamination in item means; independent model draws."""
    z = NormalDist().inv_cdf(1 - alpha / 2) + NormalDist().inv_cdf(power)
    n = len(a)
    diff = np.array([x.mean() - y.mean() for x, y in zip(a, b)])
    observed = float(diff.var(ddof=1))
    if any(len(x) < 2 for x in a + b):
        return {
            "status": "need_at_least_two_samples_per_item",
            "observed_difference_variance": observed,
        }
    va = np.array([x.var(ddof=1) for x in a])
    vb = np.array([x.var(ddof=1) for x in b])
    noise = float(np.mean([x / len(s) + y / len(t) for x, y, s, t in zip(va, vb, a, b)]))
    raw_between = observed - noise
    between = max(0.0, raw_between)
    within = float((va + vb).mean())
    if observed == 0 and within == 0:
        return {
            "status": "unidentified_zero_empirical_variance",
            "observed_difference_variance": 0.0,
        }
    grid = []
    for m in sample_grid:
        variance = between + within / m
        required = max(2, math.ceil(z * z * variance / (gap * gap)))
        target = n * (gap / z) ** 2 - between
        minimum_samples = max(1, math.ceil(within / target)) if target > 0 else None
        grid.append(
            {
                "samples_per_item_per_model": m,
                "mdd": z * math.sqrt(variance / n),
                "items_for_target_gap": required,
                "generations_per_model": required * m,
            }
        )
    return {
        "status": "approximate_pilot_projection",
        "alpha_two_sided": alpha,
        "power": power,
        "target_gap": gap,
        "between_item_variance_raw": raw_between,
        "between_item_variance": between,
        "between_variance_clipped": raw_between < 0,
        "within_item_variance_sum": within,
        "mdd_current_design": z * math.sqrt((between + noise) / n),
        "minimum_samples_at_current_items": minimum_samples,
        "grid": grid,
    }


def analyze(
    models,
    items,
    data,
    *,
    ks=(1, 5, 10),
    resamples=5000,
    seed=20261101,
    confidence=0.95,
    gap=0.05,
    alpha=0.05,
    power=0.8,
    sample_grid=(1, 3, 5, 10, 20),
):
    if resamples < 100:
        raise ValueError("use at least 100 resamples")
    if not 0 < confidence < 1 or not 0 < alpha < 1 or not 0.5 < power < 1 or not 0 < gap <= 1:
        raise ValueError("invalid confidence, alpha, power, or gap")
    if not ks or not sample_grid or any(k < 1 for k in ks) or any(m < 1 for m in sample_grid):
        raise ValueError("k and planned sample counts must be positive")
    minimum = min(len(x) for row in data for x in row)
    if max(ks) > minimum:
        raise ValueError(f"pass@{max(ks)} needs more samples: minimum available is {minimum}")
    rng = np.random.default_rng(seed)
    n, m = len(items), len(models)
    reports = {}
    for k in sorted(set(ks) | {1}):
        per_item = np.array([item_scores(row, k) for row in data])
        point = per_item.mean(axis=1)
        item_boot = np.empty((resamples, m))
        sample_boot = np.empty((resamples, m))
        # Chunk the item bootstrap to keep memory bounded on large eval files.
        for start in range(0, resamples, 128):
            stop = min(start + 128, resamples)
            indices = rng.integers(n, size=(stop - start, n))
            item_boot[start:stop] = per_item[:, indices].mean(axis=2).T
        for j, row in enumerate(data):
            # Exact empirical binary resampling is binomial; items remain fixed.
            accum = np.zeros(resamples)
            for x in row:
                counts = rng.binomial(len(x), x.mean(), size=resamples)
                lookup = np.array([pass_at_k(len(x), c, k) for c in range(len(x) + 1)])
                accum += lookup[counts]
            sample_boot[:, j] = accum / n
        modes = {}
        for mode, draws in (("items", item_boot), ("sampling", sample_boot)):
            pairs = []
            for i, j in combinations(range(m), 2):
                delta = draws[:, i] - draws[:, j]
                ties = np.isclose(delta, 0, rtol=0, atol=1e-12)
                pos = (delta > 0) & ~ties
                neg = (delta < 0) & ~ties
                observed_delta = float(point[i] - point[j])
                flip = (
                    None
                    if abs(observed_delta) <= 1e-12
                    else float((neg if observed_delta > 0 else pos).mean())
                )
                pair = {
                    "a": models[i],
                    "b": models[j],
                    "difference": observed_delta,
                    "ci": interval(delta, confidence),
                    "p_a_beats_b": float(pos.mean()),
                    "p_tie": float(ties.mean()),
                    "p_b_beats_a": float(neg.mean()),
                    "rank_flip_frequency": flip,
                }
                if k == 1 and mode == "items":
                    pair["planning"] = planning(data[i], data[j], gap, alpha, power, sample_grid)
                pairs.append(pair)
            ranks = {}
            for j, model in enumerate(models):
                # Competition rank: every model tied for best gets rank 1.
                ranks[model] = (1 + np.sum(draws > draws[:, j : j + 1] + 1e-12, axis=1)).tolist()
            modes[mode] = {
                "models": {
                    name: {
                        "estimate": float(point[j]),
                        "ci": interval(draws[:, j], confidence),
                        "bootstrap_se": float(draws[:, j].std(ddof=1)),
                        "rank_probabilities": {
                            str(r): ranks[name].count(r) / resamples for r in range(1, m + 1)
                        },
                    }
                    for j, name in enumerate(models)
                },
                "pairwise": pairs,
            }
        reports[f"pass@{k}"] = modes
    warnings = [
        "Bootstrap win fractions are resampling stability, not posterior probabilities or p-values.",
        "Item intervals resample whole observed item vectors and include finite-repeat noise; do not add their variance to sampling intervals.",
        "Sampling intervals condition on these items and empirical generation probabilities; pass@k resampling can be biased for k>1.",
        "Percentile bootstrap can collapse at boundaries or with no observed variation; a point interval does not prove certainty.",
        "Pairwise intervals are unadjusted for multiple comparisons; no familywise significance claim is made.",
        "Planning assumes independent items and independent iid generations across models; extrapolations require validation.",
    ]
    if minimum == 1:
        warnings.append("One sample per item cannot identify within-item sampling uncertainty.")
    return {
        "schema_version": 1,
        "n_items": n,
        "models": models,
        "minimum_samples": minimum,
        "samples_per_model": {name: [len(x) for x in data[j]] for j, name in enumerate(models)},
        "config": {
            "ks": sorted(set(ks) | {1}),
            "resamples": resamples,
            "seed": seed,
            "confidence": confidence,
            "gap": gap,
            "alpha": alpha,
            "power": power,
            "sample_grid": list(sample_grid),
        },
        "metrics": reports,
        "warnings": warnings,
    }
