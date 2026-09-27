#!/bin/zsh
# Rebuild the GPT-OSS 120B uncensored model on the dedicated server with Ollama's official gpt-oss chat
# template, reusing the already-verified GGUF blob. The template Ollama derived for the hf.co import was
# malformed (truncated "tart|>user" header, prefilled final channel, stop on <|channel|>), which emptied
# responses. Template source: registry.ollama.ai/library/gpt-oss:20b, layer sha256:fa6710a93d78da62...
# (application/vnd.ollama.image.template), read from the Sep 22 stock artifact store on this Mac.
set -eu
BLOB=~/Documents/Codex/model-cache/uncensored-benchmark/ollama/blobs/sha256-0ed271ff3d05ef6013e7f464766bc8555733fc24dbcb89be9ed5cf1c23299e55
TEMPLATE=$(print -l ~/Documents/Codex/model-cache/mac-benchmarks/ollama/blobs/sha256-fa6710a93d78da62*)
MODELFILE=$(mktemp)
{ print -rn -- "FROM $BLOB"$'\nTEMPLATE """'; cat "$TEMPLATE"; print -r -- '"""'; } > "$MODELFILE"
OLLAMA_HOST=127.0.0.1:11436 ollama create gptoss-120b-hauhaucs-officialtemplate:mxfp4 -f "$MODELFILE"
rm -f "$MODELFILE"
