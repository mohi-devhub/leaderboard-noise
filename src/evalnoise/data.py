"""Strict input normalization; no missing predictions are silently discarded."""

from collections import defaultdict
import json
from pathlib import Path

import numpy as np


def field(row, key):
    for part in key.split("."):
        row = row[part]
    return row


def read_rows(path):
    rows = []
    with Path(path).open() as f:
        for line, text in enumerate(f, 1):
            if not text.strip():
                continue
            try:
                row = json.loads(text)
                if not isinstance(row, dict):
                    raise ValueError("expected an object")
            except (ValueError, TypeError) as exc:
                raise ValueError(f"line {line}: {exc}") from exc
            rows.append(row)
    if not rows:
        raise ValueError("input contains no rows")
    return rows


def load(
    path,
    model_key="model",
    item_key="item_id",
    score_key="passed",
    sample_key="sample_id",
    benchmark=None,
    condition=None,
):
    rows = read_rows(path)
    if benchmark is not None:
        rows = [r for r in rows if r.get("benchmark") == benchmark]
    if condition is not None:
        rows = [r for r in rows if r.get("condition") == condition]
    if not rows:
        raise ValueError("no rows match the requested filters")
    for key in ("benchmark", "condition"):
        if len({r.get(key) for r in rows}) > 1:
            raise ValueError(f"mixed {key} values: select one with --{key}")
    values = defaultdict(dict)
    seen = set()
    shapes = {}
    prompt_hashes = {}
    for i, r in enumerate(rows, 1):
        try:
            model, item = field(r, model_key), field(r, item_key)
            if not isinstance(model, str) or not model or not isinstance(item, str) or not item:
                raise ValueError("model and item identifiers must be nonempty strings")
            key = model, item
            if "successes" in r:
                if key in shapes:
                    raise ValueError("duplicate aggregate or mixed row formats")
                scores = r["successes"]
                if not isinstance(scores, list) or not scores:
                    raise ValueError("successes must be a nonempty list")
                shapes[key] = "aggregate"
            else:
                if shapes.get(key) == "aggregate":
                    raise ValueError("mixed aggregate and sample rows")
                shapes[key] = "sample"
                sample = field(r, sample_key)
                if not isinstance(sample, (str, int)) or isinstance(sample, bool):
                    raise ValueError("sample identifier must be a string or integer")
                if (*key, sample) in seen:
                    raise ValueError("duplicate sample identifier")
                seen.add((*key, sample))
                scores = [field(r, score_key)]
            if any(type(v) not in (bool, int, float) or v not in (0, 1) for v in scores):
                raise ValueError(
                    "scores must be binary 0/1 or boolean; missing/error scores need review"
                )
            values[model].setdefault(item, []).extend(scores)
            if "prompt_sha256" in r:
                old = prompt_hashes.setdefault(item, r["prompt_sha256"])
                if old != r["prompt_sha256"]:
                    raise ValueError("prompt hash differs for the same item")
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"row {i}: {exc}") from exc
    models = sorted(values)
    items = sorted(values[models[0]])
    if len(items) < 2:
        raise ValueError("at least two items are required")
    for model in models:
        if set(values[model]) != set(items):
            raise ValueError(
                "models must have identical item sets; align explicitly before analysis"
            )
    return models, items, [[np.asarray(values[m][i], dtype=float) for i in items] for m in models]
