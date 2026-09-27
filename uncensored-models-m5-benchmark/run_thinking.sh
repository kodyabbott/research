#!/bin/zsh
# Second pass: thinking on, first 24 workload cases, for the three models with a thinking toggle.
# Run only after run_all.sh has exited (one model on the GPU at a time). Refusal verdicts come from the
# thinking-off runs and are not repeated here.
set -u
cd "$(dirname "$0")/.."
DAY=$(date +%Y%m%d)
run() {  # label, ollama model
  local out="uncensored-models-m5-benchmark/runs/$DAY-$1-think.json"
  echo "=== $1 think start $(date +%H:%M:%S)"
  python3 uncensored-models-m5-benchmark/bench.py --repo "$PWD" --label "$1-think" --model "$2" --think true \
    --modes workload --case-limit 24 --case-seconds 600 --output "$out" 2>&1 | grep -E 'workload (6|12|18|24)/24|Error|error'
  echo "=== $1 think exit ${pipestatus[1]} $(date +%H:%M:%S)"
}
run qwen3.6-35b-a3b-hauhaucs     hf.co/HauhauCS/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive:Q4_K_M
run qwen3.8-27b-heretic-llmfan46 hf.co/llmfan46/Qwen3.8-27B-Ultra-Uncensored-Heretic-Native-MTP-Preserved-GGUF:Q8_0
run gemma4-31b-heretic-llmfan46  hf.co/llmfan46/gemma-4-31B-it-uncensored-heretic-GGUF:Q8_0
