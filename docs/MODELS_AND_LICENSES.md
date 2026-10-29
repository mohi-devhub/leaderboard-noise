# Model rosters and licenses

The full study uses the user-approved six-model selection in `experiments/full-models.json`: Qwen2.5-1.5B/3B, Qwen3-1.7B, Llama3.2-3B, xLAM-2-3b-fc-r, and Qwen3-4B-Instruct-2507. The two Qwen3 checkpoints declare Apache 2.0; xLAM declares CC BY-NC 4.0 and a research release. Pinned official license/configuration sources and hashes are in `results/metadata/full-model-sources.json`. Gated Llama access was confirmed using the existing credential. See [the selection rationale](FULL_STUDY_PLAN.md). The table below preserves the original candidate roster used to plan the pilot.

Model IDs and immutable repository revisions are in `experiments/models.json`. License-text URLs and SHA256 checksums verified at official sources are in `results/metadata/license-sources.json`. No weights are redistributed by this project.

| Model | License | Access / restriction |
|---|---|---|
| [Qwen2.5-0.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct) | Apache 2.0 | Public; pilot |
| [Qwen2.5-1.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct) | Apache 2.0 | Public; pilot |
| [Qwen2.5-3B-Instruct](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct/blob/main/LICENSE) | Qwen Research License | Research/evaluation noncommercial terms; not Apache 2.0 |
| [Llama-3.2-1B-Instruct](https://huggingface.co/meta-llama/Llama-3.2-1B-Instruct) | Llama 3.2 Community License | Gated; account must have access and comply with license/AUP |
| [Llama-3.2-3B-Instruct](https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct) | Llama 3.2 Community License | Gated; account must have access and comply with license/AUP |
| [Phi-3.5-mini-instruct](https://huggingface.co/microsoft/Phi-3.5-mini-instruct/blob/main/LICENSE) | MIT | Public; sixth candidate |

The official [Llama 3.2 license](https://github.com/meta-llama/llama-models/blob/main/models/llama3_2/LICENSE) applies to both listed text models. We verified license text from Meta's repository because gated weight download requires the user's own access; public metadata does not prove that access has been granted. This pilot does not silently replace a gated model. Full-run planning must check access without printing tokens.

“Small open models” here means publicly documented open-weight candidates with differing licenses, not a claim that all are unrestricted open-source software. The roster was specified for replication, not selected after seeing favorable results. Phi-3.5-mini has approximately 3.8B parameters and fits the intended small-model comparison. Parameter count and marketing benchmark tables do not prove close ability on this frozen BFCL task.

BFCL data metadata declares Apache 2.0 in its official distributed README. Retain source attribution and benchmark hashes. The subset is limited to Python single-turn AST categories; do not describe its mean as BFCL's official overall aggregate. Code tasks remain optional and require separate CPU isolation and a post-pilot budget decision.
