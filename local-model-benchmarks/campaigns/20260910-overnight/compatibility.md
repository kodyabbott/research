# Runtime compatibility observations

Muse BF16/DFlash run `20260910-230444-966fe4d6` reported 2,464,656,915 bytes through `/api/ps`.
The [bounded log evidence](muse-memory-evidence.json) records the intended 27.85B main model
loading 53/53 layers, a 50,566.42 MiB CUDA model buffer, and a separate 1,543.17 MiB draft buffer.
The [Ollama 0.32.13 parser](https://github.com/ollama/ollama/blob/v0.32.13/llm/llama_server.go#L2772-L2783)
keys allocations by component/backend/kind, so draft entries replace the matching main entries.
Summing retained entries reproduces the reported value exactly. Treat this field as unreliable
for total residency with this configuration; it does not show that the wrong weights ran.

The experiment still has an invalid throughput comparison: all three short trials reached
512 tokens. The small visible answers versus generated-token count remain unexplained.
The separate v2 quality screen scored 15/16 versus the coder's 12/16. These observations do
not isolate whether DFlash, template behavior, or another runtime detail caused truncation.
No runtime or model configuration was changed for the audit.

[Ollama's exact-version GPT-OSS documentation](https://github.com/ollama/ollama/blob/v0.32.13/docs/capabilities/thinking.mdx#L69-L73)
says boolean thinking values are ignored and low/medium/high are supported. GPT-OSS therefore
has a separate explicit-low screen, not an asserted thinking-off comparison. Its output budget
is 8192 tokens per case rather than the main sweep's 512, and its scores must be labeled accordingly.
