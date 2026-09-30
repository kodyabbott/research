# Research

AI agent safety research by [Kody Abbott](https://kodyabbott.com). Learning in public.

Each folder is a research project. `notes.md` is the trail, `README.md` is the report.

Research is AI-assisted using Claude Code (Anthropic; currently Claude Fable 5, earlier projects Opus 4.6). I direct and verify, the agent searches and drafts. Project READMEs are marked with an `AI-ASSISTED-NOTE` banner to make this transparent. See [CLAUDE.md](CLAUDE.md) for what that means and how this repo works.

Repo structure based on Simon Willison's [simonw/research](https://github.com/simonw/research). Simon's work on the [Lethal Trifecta](https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/) and [prompt injection](https://simonwillison.net/series/prompt-injection/) is a primary source here.

## How it works

The `.claude/` directory contains the agent team that runs this research:
- `agents/` -- specialized agents (researcher, source-verifier, adversarial-reviewer, url-auditor)
- `rules/` -- research workflow and source verification rules, auto-loaded every session
- `settings.json` -- project permissions and model config

See [CLAUDE.md](CLAUDE.md) for full agent instructions.

## Projects

- [jensen-gtc-agent-safety](jensen-gtc-agent-safety/) -- Jensen Huang's GTC comments on AI agent capability constraints
- [simon-willison-lenny-podcast](simon-willison-lenny-podcast/) -- Simon Willison on Lenny's Podcast: AI state of the union, lethal trifecta, and agent security
- [local-model-benchmarks](local-model-benchmarks/) -- Same-day benchmarks of trending open models on one known machine, with methodology stated so the numbers can be argued with
- [mac-model-benchmarks](mac-model-benchmarks/) -- M5 Max measurements using native MLX and matched Ollama artifacts, with Windows references, raw results, and rerun commands
- [mac-model-guide-2026-09](mac-model-guide-2026-09/) -- September 2026 local-model recommendations for the M5 Max 128 GB, with category picks, verified artifact sizes, and benchmark priorities
- [deepseek-v4-flash-m5-benchmark](deepseek-v4-flash-m5-benchmark/) -- DeepSeek V4 Flash speed and strict practical-task results on the M5 Max, with temperature/fan telemetry and an expanded model shortlist
- [uncensored-models-m5-benchmark](uncensored-models-m5-benchmark/) -- Five uncensored Hugging Face models (Heretic, abliterated, HauhauCS) ranked on the M5 Max by the 96-case JSON suite, thinking on and off, speed, and Heretic's refusal scorer, with pinned artifacts, raw runs, and the GPT-OSS template fix
- [stock-qwen-m5-benchmark](stock-qwen-m5-benchmark/) -- Stock Qwen3.8-27B Q8_0 and Qwen3.8-Flash-Next 3-bit on the M5 Max: both 24/24 with thinking on, Flash-Next about 2.6x faster; 23/24 byte-identical answers vs the Windows BF16 run, stock vs Heretic comparison, sharded-GGUF import workaround, raw runs
- [anthropic-only-company-x-thread](anthropic-only-company-x-thread/) -- The Aug 2026 Baker/Douglas/Amodei X exchange on Anthropic, regulation, and open weights: curated full-text report of the public figures, IDs-only dataset (X Developer Policy), and collection cost analysis (X API vs browser automation)
