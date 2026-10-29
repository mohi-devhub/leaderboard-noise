"""Paired item resampling for batch-induced rank changes, with explicit CI limits."""

from statistics import NormalDist

import numpy as np


def wilson(successes, total, confidence=0.95):
    if total <= 0 or not 0 <= successes <= total:
        raise ValueError("invalid binomial counts")
    z = NormalDist().inv_cdf((1 + confidence) / 2)
    p = successes / total
    scale = 1 + z * z / total
    center = (p + z * z / (2 * total)) / scale
    radius = z * np.sqrt(p * (1 - p) / total + z * z / (4 * total**2)) / scale
    return [max(0.0, float(center - radius)), min(1.0, float(center + radius))]


def flip_summary(delta, *, seed, resamples=5000, outer=500, inner=1000, kind="batch"):
    """Resample joint item patterns; outer intervals are exploratory, not calibrated at ties."""
    delta = np.asarray(delta, dtype=float)
    if delta.ndim == 1:
        delta = delta[:, None]
    if delta.ndim != 2 or delta.shape[0] < 2 or not np.isfinite(delta).all():
        raise ValueError("need finite paired item differences")
    if kind not in {"batch", "sampling"}:
        raise ValueError("unknown flip definition")
    point = delta.mean(axis=0)
    sign = np.where(abs(point) <= 1e-12, 0, np.sign(point))
    if kind == "sampling" and (delta.shape[1] != 1 or sign[0] == 0):
        return {
            "estimate": None,
            "ci95": None,
            "reason": "observed tie or invalid scalar reference",
        }
    if kind == "batch" and delta.shape[1] < 2:
        raise ValueError("batch flips require at least two configurations")

    def flips(values):
        if kind == "batch":
            return np.any(values > 1e-12, axis=1) & np.any(values < -1e-12, axis=1)
        return values[:, 0] * sign[0] < -1e-12

    patterns, counts = np.unique(delta, axis=0, return_counts=True)
    n = len(delta)
    probs = counts / n
    rng = np.random.default_rng(seed)
    draws = rng.multinomial(n, probs, size=resamples) @ patterns / n
    indicators = flips(draws)
    outer_counts = rng.multinomial(n, probs, size=outer)
    outer_rates = np.empty(outer)
    for index, count in enumerate(outer_counts):
        nested = rng.multinomial(n, count / n, size=inner) @ patterns / n
        outer_rates[index] = flips(nested).mean()
    ci = [float(x) for x in np.quantile(outer_rates, [0.025, 0.975])]
    return {
        "definition": "opposite strict orders across batch settings"
        if kind == "batch"
        else "strict reversal of the fixed observed stochastic order",
        "estimate": float(indicators.mean()),
        "ci95": ci,
        "interval_kind": "exploratory outer paired-item bootstrap percentile interval",
        "mc_wilson95": wilson(int(indicators.sum()), resamples),
        "mc_interval_kind": "Monte Carlo precision conditional on the empirical dataset; not population uncertainty",
        "observed_differences": point.tolist(),
        "observed_strict_flip": bool(flips(point[None, :])[0]),
        "difference_ci95": np.quantile(draws, [0.025, 0.975], axis=0).T.tolist(),
        "any_tie_fraction": float(np.any(abs(draws) <= 1e-12, axis=1).mean()),
        "resamples": resamples,
        "outer_resamples": outer,
        "inner_resamples": inner,
        "seed": seed,
        "collapsed_outer_interval": ci[0] == ci[1],
        "warning": "Discontinuous order statistics and absent empirical patterns can collapse these intervals; they do not prove no population flips. Inner Monte Carlo noise also contributes to outer interval width.",
    }
