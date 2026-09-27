#!/bin/zsh
# Follow-ups from the adversarial review, run after run_thinking.sh (one model on the GPU at a time):
# 1. GPT-OSS refusal pass comparable to the others: raw harmony prompt with Heretic's gpt-oss
#    chain_of_thought_skip (closed empty analysis block), 100-token cap, verdicts only.
# 2. Qwen3.8-27B Heretic thinking on across all 96 cases, so the top two are compared on the same case count.
set -u
cd "$(dirname "$0")/.."
DAY=$(date +%Y%m%d)
B=uncensored-models-m5-benchmark
echo "=== gpt-oss refusal-prefill start $(date +%H:%M:%S)"
python3 $B/bench.py --repo "$PWD" --label gpt-oss-120b-hauhaucs-refusal-prefill --model gptoss-120b-hauhaucs-officialtemplate:mxfp4 \
  --think low --modes refusal --harmony-prefill --refusal-cap 100 --output $B/runs/$DAY-gpt-oss-120b-hauhaucs-refusal-prefill.json 2>&1 | tail -3
echo "=== gpt-oss refusal-prefill exit ${pipestatus[1]} $(date +%H:%M:%S)"
echo "=== qwen3.8 think96 start $(date +%H:%M:%S)"
python3 $B/bench.py --repo "$PWD" --label qwen3.8-27b-heretic-llmfan46-think96 --model hf.co/llmfan46/Qwen3.8-27B-Ultra-Uncensored-Heretic-Native-MTP-Preserved-GGUF:Q8_0 \
  --think true --modes workload --case-limit 96 --case-seconds 600 --output $B/runs/$DAY-qwen3.8-27b-heretic-llmfan46-think96.json 2>&1 | tail -3
echo "=== qwen3.8 think96 exit ${pipestatus[1]} $(date +%H:%M:%S)"
