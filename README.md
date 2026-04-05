# Research

AI agent safety research by [Kody Abbott](https://kodyabbott.com). Learning in public.

Each folder is a research project. `notes.md` is the trail, `README.md` is the report.

Research is AI-assisted using Claude Code (Anthropic, Opus 4.6 1M context). I direct and verify, the agent searches and drafts. Project READMEs are marked with an `AI-ASSISTED-NOTE` banner to make this transparent. See [CLAUDE.md](CLAUDE.md) for what that means and how this repo works.

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
