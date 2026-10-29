"""CPU-only pinned tokenizer check; the GPU worker repeats the authoritative check."""

import hashlib
import importlib.metadata
import json
from pathlib import Path

from transformers import AutoTokenizer


def main():
    config = json.loads(Path("experiments/full-study.json").read_text())
    items = [
        json.loads(line) for line in Path("experiments/bfcl-items.jsonl").read_text().splitlines()
    ]
    reports = []
    for model in json.loads(Path("experiments/full-models.json").read_text()):
        tokenizer = AutoTokenizer.from_pretrained(
            model["id"],
            revision=model["revision"],
            trust_remote_code=False,
            cache_dir=".uv-cache/huggingface",
        )
        prompts = [
            tokenizer.apply_chat_template(
                item["messages"],
                tokenize=False,
                add_generation_prompt=True,
                **model.get("chat_template_kwargs", {}),
            )
            for item in items
        ]
        lengths = [len(tokenizer.encode(prompt, add_special_tokens=False)) for prompt in prompts]
        report = {
            "model": model["id"],
            "revision": model["revision"],
            "items": len(items),
            "maximum_prompt_tokens": max(lengths),
            "context_limit": config["max_model_len"],
            "output_limit": config["max_tokens"],
            "passes_context_check": max(lengths) + config["max_tokens"] <= config["max_model_len"],
            "transformers": importlib.metadata.version("transformers"),
            "tokenizers": importlib.metadata.version("tokenizers"),
            "rendered_prompt_sha256": [
                hashlib.sha256(prompt.encode()).hexdigest() for prompt in prompts
            ],
            "note": "CPU tokenizer version may differ from pinned GPU environment; GPU worker validates every prompt and records its own hashes before inference.",
        }
        reports.append(report)
        print(
            {k: v for k, v in report.items() if k not in {"rendered_prompt_sha256", "note"}},
            flush=True,
        )
        Path("results/metadata/full-prompt-preflight.json").write_text(
            json.dumps(reports, indent=2) + "\n"
        )
        if not report["passes_context_check"]:
            raise RuntimeError("full prompt cannot fit configured context")


if __name__ == "__main__":
    main()
