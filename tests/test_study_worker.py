import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


@pytest.mark.parametrize(
    "arm,timing_only,expected,include_sampling,collect_timing",
    [
        ("default", False, 58, True, True),
        ("batch_invariant", False, 18, True, True),
        ("default", True, 6, True, True),
        ("default", False, 12, False, False),
        ("batch_invariant", False, 12, False, False),
    ],
)
@pytest.mark.parametrize("model_id", ["model", "meta-llama/Llama-3.2-3B-Instruct"])
def test_worker_keeps_timing_repeats_separate_from_accuracy(
    monkeypatch, tmp_path, arm, timing_only, expected, model_id, include_sampling, collect_timing
):
    class Params:
        def __init__(self, **values):
            self.__dict__.update(values)

    templates = []
    generation_calls = []

    class Tokenizer:
        def apply_chat_template(self, messages, **kwargs):
            templates.append(kwargs)
            return messages[0]["content"]

        def encode(self, text, **kwargs):
            return [1]

    class LLM:
        def __init__(self, **kwargs):
            pass

        def get_tokenizer(self):
            return Tokenizer()

        def generate(self, prompts, params, **kwargs):
            generation_calls.append((prompts, kwargs))
            if not isinstance(params, list):
                params = [params] * len(prompts)
            return [
                SimpleNamespace(
                    outputs=[
                        SimpleNamespace(text="[f(x=1)]", token_ids=[1, 2], finish_reason="stop")
                        for _ in range(getattr(p, "n", 1))
                    ]
                )
                for p in params
            ]

    monkeypatch.setitem(sys.modules, "vllm", SimpleNamespace(LLM=LLM, SamplingParams=Params))
    monkeypatch.setitem(
        sys.modules,
        "torch",
        SimpleNamespace(
            version=SimpleNamespace(cuda="test"),
            cuda=SimpleNamespace(
                synchronize=lambda: None,
                get_device_name=lambda: "NVIDIA A10",
                get_device_capability=lambda: (8, 6),
            ),
        ),
    )
    path = Path(__file__).parents[1] / "scripts/gpu_worker.py"
    spec = importlib.util.spec_from_file_location("study_worker_test", path)
    worker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(worker)
    monkeypatch.setattr(worker.subprocess, "check_output", lambda *a, **k: "test-driver")
    payload, output = tmp_path / "input.json", tmp_path / "output.json"
    value = {
        "config": {
            "seed": 42,
            "n": 10,
            "temperature": 0.7,
            "top_p": 1,
            "max_tokens": 512,
            "max_model_len": 8192,
            "greedy_repeats": [
                {"run_id": f"batch{size}", "request_batch_size": size} for size in (1, 8, 32)
            ],
        },
        "model": {
            "id": model_id,
            "revision": "pinned",
            "chat_template_kwargs": {"enable_thinking": False},
        },
        "model_index": 1,
        "items": [
            {
                "item_id": str(i),
                "messages": [{"content": str(i)}],
                "messages_sha256": "hash",
                "seed_index": i,
            }
            for i in range(4)
        ],
        "timing_item_ids": ["0", "2"],
        "timing_repeat_index": 2,
        "timing_only": timing_only,
        "include_sampling": include_sampling,
    }
    if not collect_timing:
        value.pop("timing_repeat_index")
    payload.write_text(json.dumps(value))
    monkeypatch.setattr(sys, "argv", [str(path), str(payload), str(output), "--arm", arm])
    worker.main()
    result = json.loads(output.read_text())
    rows = result["rows"]
    assert len(rows) == expected
    assert len({(r["item_id"], r["condition"], r["sample_id"]) for r in rows}) == expected
    timing = [r for r in rows if r["phase"] == "timing"]
    assert len(timing) == (6 if collect_timing else 0)
    assert {r["item_id"] for r in timing} == ({"0", "2"} if collect_timing else set())
    assert all(r["condition"].startswith(f"timing:{arm}:repeat2:") for r in timing)
    assert all(t["enable_thinking"] is False for t in templates)
    assert sum(t["completions"] for t in result["metadata"]["timings"]) == expected
    for prompts, kwargs in generation_calls:
        if prompts != ["Say hello."] * 5:
            assert kwargs["tokenization_kwargs"] == (
                {"add_special_tokens": False} if model_id.startswith("meta-llama/") else None
            )
