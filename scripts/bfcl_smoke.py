"""Check the official checker under security overrides, using a hand-verifiable fixture."""

from score_bfcl import score_one


item = {
    "item_id": "simple_python_smoke",
    "category": "simple_python",
    "question": {
        "function": [
            {
                "name": "calc.add",
                "description": "Add integers.",
                "parameters": {
                    "type": "dict",
                    "properties": {
                        "a": {"type": "integer", "description": "First integer"},
                        "b": {"type": "integer", "description": "Second integer"},
                    },
                    "required": ["a", "b"],
                },
            }
        ]
    },
    "ground_truth": [{"calc.add": {"a": [2], "b": [3]}}],
}
assert score_one({"model": "Qwen/Qwen2.5-0.5B-Instruct", "output": "[calc.add(a=2,b=3)]"}, item)[0]
assert not score_one(
    {"model": "Qwen/Qwen2.5-0.5B-Instruct", "output": "[calc.add(a=2,b=4)]"}, item
)[0]
assert not score_one({"model": "Qwen/Qwen2.5-0.5B-Instruct", "output": "invalid syntax!"}, item)[0]
print("Official BFCL checker smoke checks passed (correct, incorrect, malformed)")
