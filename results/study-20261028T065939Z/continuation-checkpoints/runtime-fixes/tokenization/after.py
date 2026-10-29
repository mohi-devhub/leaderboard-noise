"""One model/arm per fresh process. This file alone is copied into the GPU image."""

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import time


def request_seed(root, model_index, item_index):
    """Disjoint n<=100 seed blocks, independent of request batching and item order."""
    if not 0 <= model_index < 100 or not 0 <= item_index < 10000:
        raise ValueError("seed allocation indices out of range")
    return root + model_index * 1_000_000 + item_index * 100


def main():
    p = argparse.ArgumentParser()
    p.add_argument("payload", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--arm", choices=["default", "batch_invariant"], required=True)
    p.add_argument("--smoke-only", action="store_true")
    args = p.parse_args()
    payload = json.loads(args.payload.read_text())
    config, model, items = payload["config"], payload["model"], payload["items"]
    worker_source_sha256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    tokenization_kwargs = (
        {"add_special_tokens": False} if model["id"] == "meta-llama/Llama-3.2-3B-Instruct" else None
    )
    if any("seed_index" not in item for item in items):
        raise ValueError("all inference items require their frozen seed_index")
    os.environ["VLLM_BATCH_INVARIANT"] = "1" if args.arm == "batch_invariant" else "0"
    os.environ["VLLM_NO_USAGE_STATS"] = "1"
    os.environ["DO_NOT_TRACK"] = "1"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    from vllm import LLM, SamplingParams
    import torch

    start = time.perf_counter()
    llm = LLM(
        model=model["id"],
        revision=model["revision"],
        tokenizer_revision=model["revision"],
        dtype="bfloat16",
        trust_remote_code=False,
        load_format="safetensors",
        tensor_parallel_size=1,
        max_model_len=config["max_model_len"],
        gpu_memory_utilization=0.85,
        max_num_seqs=64,
        enforce_eager=True,
        enable_prefix_caching=False,
        seed=config["seed"],
    )
    tokenizer = llm.get_tokenizer()
    prompts = [
        tokenizer.apply_chat_template(
            r["messages"],
            tokenize=False,
            add_generation_prompt=True,
            **model.get("chat_template_kwargs", {}),
        )
        for r in items
    ]
    token_lengths = [len(tokenizer.encode(p, add_special_tokens=False)) for p in prompts]
    if any(n + config["max_tokens"] > config["max_model_len"] for n in token_lengths):
        raise RuntimeError(
            "frozen prompt exceeds context; do not silently drop or truncate an item"
        )
    startup = time.perf_counter() - start
    # Five non-benchmark smoke requests. A failure stops this model before pilot generation.
    smoke_start = time.perf_counter()
    smoke = llm.generate(
        ["Say hello."] * 5,
        SamplingParams(temperature=0, max_tokens=8, seed=config["seed"]),
        use_tqdm=False,
    )
    if len(smoke) != 5 or any(not r.outputs or not r.outputs[0].token_ids for r in smoke):
        raise RuntimeError("vLLM five-request smoke test failed")
    smoke_seconds = time.perf_counter() - smoke_start
    if args.smoke_only:
        args.output.write_text(
            json.dumps(
                {
                    "passed": True,
                    "model": model,
                    "arm": args.arm,
                    "requests": 5,
                    "startup_seconds": startup,
                    "smoke_seconds": smoke_seconds,
                    "outputs": [
                        {"text": r.outputs[0].text, "token_ids": list(r.outputs[0].token_ids)}
                        for r in smoke
                    ],
                    "gpu": torch.cuda.get_device_name(),
                    "vllm": importlib.metadata.version("vllm"),
                }
            )
        )
        return
    rows, timings = [], []
    conditions = []
    evaluation = not payload.get("timing_only", False)
    if args.arm == "default" and evaluation:
        conditions.append(
            {
                "run_id": "sampling",
                "request_batch_size": 16,
                "temperature": config["temperature"],
                "n": config["n"],
            }
        )
    if evaluation:
        conditions += [{**r, "temperature": 0, "n": 1} for r in config["greedy_repeats"]]
    if "timing_repeat_index" in payload:
        conditions += [
            {
                **r,
                "temperature": 0,
                "n": 1,
                "phase": "timing",
                "repeat_index": payload["timing_repeat_index"],
            }
            for r in config["greedy_repeats"]
        ]
    for condition in conditions:
        phase = condition.get("phase", "evaluation")
        selected = (
            [i for i, r in enumerate(items) if r["item_id"] in payload["timing_item_ids"]]
            if phase == "timing"
            else list(range(len(items)))
        )
        run_items = [items[i] for i in selected]
        run_prompts = [prompts[i] for i in selected]
        repeat = condition.get("repeat_index")
        label = (
            f"timing:{args.arm}:repeat{repeat}:{condition['run_id']}"
            if phase == "timing"
            else "sampling"
            if condition["run_id"] == "sampling"
            else f"{args.arm}:{condition['run_id']}"
        )
        print(f"EVALNOISE_CONDITION {model['id']} {label} N={len(run_items)}", flush=True)
        # Match steady-state warmup across arms/configurations; report it separately.
        params = [
            SamplingParams(
                n=condition["n"],
                temperature=condition["temperature"],
                top_p=config["top_p"],
                max_tokens=config["max_tokens"],
                seed=request_seed(config["seed"], payload["model_index"], r["seed_index"]),
            )
            for r in run_items
        ]
        batch_size = condition["request_batch_size"]
        warm_start = time.perf_counter()
        llm.generate(
            run_prompts[:batch_size],
            params[:batch_size],
            use_tqdm=False,
            tokenization_kwargs=tokenization_kwargs,
        )
        warm_seconds = time.perf_counter() - warm_start
        torch.cuda.synchronize()
        clock = time.perf_counter()
        token_count = 0
        for offset in range(0, len(run_items), batch_size):
            batch = llm.generate(
                run_prompts[offset : offset + batch_size],
                params[offset : offset + batch_size],
                use_tqdm=False,
                tokenization_kwargs=tokenization_kwargs,
            )
            if len(batch) != len(run_items[offset : offset + batch_size]):
                raise RuntimeError("incomplete vLLM response batch")
            for j, response in enumerate(batch):
                item = run_items[offset + j]
                if len(response.outputs) != condition["n"]:
                    raise RuntimeError("incomplete vLLM n outputs")
                for index, output in enumerate(response.outputs):
                    token_count += len(output.token_ids)
                    rows.append(
                        {
                            "model": model["id"],
                            "revision": model["revision"],
                            "item_id": item["item_id"],
                            "sample_id": index,
                            "sampling_seed": request_seed(
                                config["seed"], payload["model_index"], item["seed_index"]
                            )
                            + index,
                            "benchmark": "BFCL_v4_python_ast_subset",
                            "arm": args.arm,
                            "condition": label,
                            "phase": phase,
                            "timing_repeat_index": repeat,
                            "run_id": condition["run_id"],
                            "temperature": condition["temperature"],
                            "batch_size": batch_size,
                            "max_num_seqs": 64,
                            "output": output.text,
                            "token_ids": list(output.token_ids),
                            "finish_reason": output.finish_reason,
                            "messages_sha256": item["messages_sha256"],
                            "rendered_prompt_sha256": hashlib.sha256(
                                run_prompts[offset + j].encode()
                            ).hexdigest(),
                        }
                    )
        torch.cuda.synchronize()
        elapsed = time.perf_counter() - clock
        completions = len(run_items) * condition["n"]
        timings.append(
            {
                "run_id": condition["run_id"],
                "arm": args.arm,
                "phase": phase,
                "repeat_index": repeat,
                "items": len(run_items),
                "request_batch_size": batch_size,
                "max_num_seqs": 64,
                "elapsed_seconds": elapsed,
                "warmup_seconds": warm_seconds,
                "completions": completions,
                "generated_tokens": token_count,
                "completions_per_second": completions / elapsed,
                "generated_tokens_per_second": token_count / elapsed,
            }
        )
    metadata = {
        "model": model,
        "arm": args.arm,
        "startup_seconds": startup,
        "smoke_seconds": smoke_seconds,
        "smoke_requests": 5,
        "timings": timings,
        "prompt_token_counts": token_lengths,
        "python": platform.python_version(),
        "gpu": torch.cuda.get_device_name(),
        "cuda": torch.version.cuda,
        "gpu_capability": torch.cuda.get_device_capability(),
        "driver": subprocess.check_output(
            ["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"], text=True
        ).strip(),
        "packages": {d.metadata["Name"]: d.version for d in importlib.metadata.distributions()},
        "vllm_batch_invariant": os.environ["VLLM_BATCH_INVARIANT"],
        "engine": {
            "enforce_eager": True,
            "enable_prefix_caching": False,
            "max_num_seqs": 64,
            "dtype": "bfloat16",
        },
        "tokenization_kwargs": tokenization_kwargs,
        "worker_source_sha256": worker_source_sha256,
    }
    args.output.write_text(json.dumps({"rows": rows, "metadata": metadata}))


if __name__ == "__main__":
    main()
