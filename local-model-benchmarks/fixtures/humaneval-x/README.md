# HumanEval-X JavaScript source and local adaptations

Source: https://huggingface.co/datasets/zai-org/humaneval-x

Dataset revision: `62c78627f3072a1454fa0cb0184737cafe5e4198`.
Original JavaScript JSONL SHA256: `1ffbb18b60d36c50c8a7d1230b7fbb82e5dd838d341242aab1caa2f8d7b598eb`.
The file is preserved byte-for-byte, including reference solutions and tests, under its Apache-2.0 license. The accompanying LICENSE was obtained from CodeGeeX revision `2838420b7b4492cf3d16bce5320e26e65960c9e2`.

Reference: Zheng et al., CodeGeeX: A Pre-Trained Model for Code Generation with Multilingual Benchmarking on HumanEval-X, KDD 2023, pp. 5673-5684. https://arxiv.org/abs/2303.17568

The local `humaneval-x-js-wasm-v1` adapter evaluates 163 of 164 tasks. JavaScript/162 requires Node crypto in its canonical solution and is excluded because the guest has no module loader. Tests 32, 119, and 151 define but never invoke their test functions; the adapter appends those invocations. Original tests are otherwise preserved. Math.random uses xorshift32 seed 42 per task. Console assertions are counted in a frozen guest console and cannot be disabled by assigning console.assert. Zero assertions cannot pass. Every task receives a fresh WASM runtime with a 64 MiB guest memory limit, 512 KiB stack, and 2-second execution deadline. The outer host subprocess has a 30-second deadline. No host APIs are exposed.

All 163 canonical solutions passed the adapted tests. Negative checks confirm that false assertions, attempted assertion replacement, and infinite loops fail; host process, require, and fetch are absent. Reference solutions and tests are never included in model requests. Models receive the original prefix plus a chat instruction to return only its continuation; only a whole Markdown fence may be removed. The continuation is appended to the unchanged source prefix, without extracting or repairing a solution based on tests.

The model protocol uses temperature 0, seed 42, 16384 context, 4096 output tokens with thinking off or 8192 with reasoning, and 240 seconds per generation within the original shared one-hour worker deadline. One sample is generated per task. Report the observed greedy success rate for this adapted protocol, not the paper's 200-sample pass@k leaderboard score. This longstanding public benchmark may have training-data overlap and does not establish unseen-task, repository-agent, or production performance.


## Chat prompt variant

The initial `humaneval-x-js-wasm-v1` continuation pilot scored 6/20 for Qwen3-Coder; all 14 failures were syntax/format failures after blindly appending the response to the source prefix. This is retained as a format-compatibility observation.

The separate `humaneval-x-js-wasm-chat-v2` protocol asks for a complete JavaScript program, including the supplied declaration and helpers. Its output is evaluated as a complete program; no prefix is appended and no generated code is repaired against tests. Full-program reference probes, including helper functions and repaired test invocations, passed. Prompt styles have separate suite digests and results; the earlier continuation pilot is not pooled with the chat variant.
