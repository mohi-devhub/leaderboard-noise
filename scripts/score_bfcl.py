"""Official BFCL AST evaluation with a thin transport adapter, no custom correctness rules."""

import argparse
from collections import defaultdict
import copy
import importlib.metadata
import json
from pathlib import Path
from types import SimpleNamespace


def score_one(row, item):
    from bfcl_eval.constants.enums import Language, ReturnFormat
    from bfcl_eval.constants.model_config import MODEL_CONFIG_MAPPING
    from bfcl_eval.eval_checker.eval_runner import _evaluate_single_ast_entry
    from bfcl_eval.model_handler.utils import default_decode_ast_prompting

    # Only the function-name normalization flag is used for these Python AST categories.
    # Register the true model name without replacing or modifying upstream checker code.
    alias = copy.copy(MODEL_CONFIG_MAPPING["gorilla-openfunctions-v2"])
    alias.model_name = row["model"]
    alias.underscore_to_dot = False
    MODEL_CONFIG_MAPPING[row["model"].replace("_", "/")] = alias
    result = _evaluate_single_ast_entry(
        SimpleNamespace(decode_ast=default_decode_ast_prompting),
        item["item_id"],
        row["output"],
        copy.deepcopy(item["ground_truth"]),
        copy.deepcopy(item["question"]),
        row["model"],
        item["category"],
        Language.PYTHON,
        ReturnFormat.PYTHON,
    )
    # Malformed syntax is a scored model failure; checker exceptions propagate and stop.
    return bool(result["valid"]), result.get("error_type")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("input", type=Path)
    p.add_argument("output", type=Path)
    args = p.parse_args()
    if importlib.metadata.version("bfcl-eval") != "2026.3.23":
        raise RuntimeError("unexpected BFCL version")
    items = {
        r["item_id"]: r
        for r in map(json.loads, Path("experiments/bfcl-items.jsonl").read_text().splitlines())
    }
    rows = [json.loads(r) for r in args.input.read_text().splitlines() if r.strip()]
    seen, counts = set(), defaultdict(int)
    for r in rows:
        key = r["model"], r["item_id"], r["condition"], r["sample_id"]
        if key in seen:
            raise ValueError("duplicate raw prediction")
        seen.add(key)
        item = items[r["item_id"]]
        if r["messages_sha256"] != item["messages_sha256"]:
            raise ValueError("messages changed after freezing")
        r["passed"], r["error_type"] = score_one(r, item)
        r["scorer"] = "bfcl-eval==2026.3.23:_evaluate_single_ast_entry"
        counts[(r["model"], r["condition"])] += 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    print(f"Scored {len(rows)} predictions with official BFCL harness")


if __name__ == "__main__":
    main()
