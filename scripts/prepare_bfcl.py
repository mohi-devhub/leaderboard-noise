"""Freeze a nested subset and prompts using the installed official BFCL package."""

import copy
import hashlib
import importlib.metadata
import json
from pathlib import Path
import random


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def main():
    from bfcl_eval.model_handler.utils import system_prompt_pre_processing_chat_model

    config = json.loads(Path("experiments/pilot.json").read_text())
    dist = importlib.metadata.distribution("bfcl-eval")
    if dist.version != "2026.3.23":
        raise RuntimeError("unexpected BFCL version")
    rng = random.Random(config["seed"])
    selected, pilot, hashes = [], [], {}
    for category, count in config["categories"].items():
        root = Path(dist.locate_file("bfcl_eval/data"))
        qpath = root / f"BFCL_v4_{category}.json"
        apath = root / "possible_answer" / qpath.name
        for p in (qpath, apath):
            hashes[str(p.relative_to(root))] = hashlib.sha256(p.read_bytes()).hexdigest()
        questions = [json.loads(x) for x in qpath.read_text().splitlines() if x.strip()]
        answers = [json.loads(x) for x in apath.read_text().splitlines() if x.strip()]
        if [r["id"] for r in questions] != [r["id"] for r in answers]:
            raise RuntimeError("question/answer alignment differs")
        indices = rng.sample(range(len(questions)), count)
        for position, index in enumerate(indices):
            q, answer = questions[index], answers[index]
            if len(q["question"]) != 1:
                raise RuntimeError("subset must be single-turn")
            messages = system_prompt_pre_processing_chat_model(
                copy.deepcopy(q["question"][0]), copy.deepcopy(q["function"]), q["id"]
            )
            record = {
                "item_id": q["id"],
                "category": category,
                "messages": messages,
                "messages_sha256": digest(messages),
                "question": q,
                "ground_truth": answer["ground_truth"],
            }
            selected.append(record)
            if position < count * config["items"] // config["full_subset_items"]:
                pilot.append(q["id"])
    out = Path("experiments/bfcl-items.jsonl")
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in selected))
    manifest = {
        "benchmark": "BFCL_v4_python_ast_subset",
        "bfcl_version": dist.version,
        "seed": config["seed"],
        "selection": "stratified stdlib Random.sample",
        "source_sha256": hashes,
        "file_sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
        "full_ids": [r["item_id"] for r in selected],
        "pilot_ids": pilot,
        "prompt_mode": "official BFCL default prompting-mode Python calls",
    }
    Path("experiments/subset.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Frozen {len(selected)} items and nested {len(pilot)}-item pilot")


if __name__ == "__main__":
    main()
