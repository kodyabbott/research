#!/bin/zsh
# Run bench.py for each selected model, one at a time, on the dedicated 11436 server.
set -u
cd "$(dirname "$0")/.."
DAY=$(date +%Y%m%d)
run() {  # label, ollama model, think, refusal cap, [stop JSON]
  local out="uncensored-models-m5-benchmark/runs/$DAY-$1.json"
  echo "=== $1 start $(date +%H:%M:%S)"
  python3 uncensored-models-m5-benchmark/bench.py --repo "$PWD" --label "$1" --model "$2" --think "$3" \
    --refusal-cap "$4" ${5:+--stop=$5} --output "$out" 2>&1 | grep -E 'workload (24|48|72|96)/96|refusal|Error|error'
  echo "=== $1 exit ${pipestatus[1]} $(date +%H:%M:%S)"
}
run qwen3.6-35b-a3b-hauhaucs     hf.co/HauhauCS/Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive:Q4_K_M                  false 100
run qwen3.8-27b-heretic-llmfan46 hf.co/llmfan46/Qwen3.8-27B-Ultra-Uncensored-Heretic-Native-MTP-Preserved-GGUF:Q8_0   false 100
run gemma4-31b-heretic-llmfan46  hf.co/llmfan46/gemma-4-31B-it-uncensored-heretic-GGUF:Q8_0                           false 100
run qwen3-coder-next-huihui      hf.co/bartowski/huihui-ai_Qwen3-Coder-Next-abliterated-GGUF:Q4_K_M                   false 100
# GPT-OSS cannot disable reasoning; reasoning tokens count against num_predict, so the refusal cap is raised
# and only the final answer channel is classified. The hf.co import got a malformed derived template, so this
# uses the same verified blob rebuilt with Ollama's official gpt-oss template (make_gptoss_model.sh).
run gpt-oss-120b-hauhaucs        gptoss-120b-hauhaucs-officialtemplate:mxfp4                                          low   1024
