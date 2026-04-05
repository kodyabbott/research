# Automation & Iteration Plan

Roadmap for bringing this repo closer to [simonw/research](https://github.com/simonw/research) and eventually adding a TIL system.

## What Simon Has (our target)

| Feature | Simon's Implementation | Status Here |
|---------|----------------------|-------------|
| CLAUDE.md / AGENTS.md | `CLAUDE.md` symlinks to `AGENTS.md` | `CLAUDE.md` is source; symlink `AGENTS.md` when needed |
| .gitignore | `.DS_Store`, `__pycache__`, `node_modules/` | ✅ Done |
| Per-project notes.md | Running log of process | ✅ Done |
| Per-project README.md | Polished report with AI-GENERATED-NOTE banner | ✅ Done (AI-ASSISTED-NOTE variant) |
| Auto-generated _summary.md | LLM generates one-paragraph summary post-commit | Not yet |
| Auto-updated root README | cogapp + GitHub Actions rebuilds project index on push | Not yet |
| requirements.txt | cogapp, llm, llm-github-models | Not yet |
| PR-based workflow | Each research project submitted as a PR with prompt in body | Not yet |

## Phase 1: Ship It (now)
- [x] Repo structure matching simonw/research
- [x] CLAUDE.md with agent instructions and attribution
- [x] Two research projects with notes.md + README.md
- [x] .gitignore
- [x] LICENSE
- [ ] Create GitHub repo, initial commit, push
- [ ] Verify README renders correctly on GitHub

## Phase 2: Automation
- [ ] Add GitHub Actions workflow for auto-updating root README.md
  - Simon uses [cogapp](https://github.com/ned-batchelder/cog) with embedded Python in README.md
  - Lists all project folders sorted by first commit date
  - Runs on push to main
- [ ] Add _summary.md auto-generation
  - Simon uses `llm` CLI with `github/gpt-4.1` model
  - Generates one-paragraph summary per project after commit
  - We could use Claude via `llm-anthropic` plugin instead
- [ ] Add requirements.txt (cogapp, llm, llm-anthropic)
- [ ] PR workflow: submit each new research project as a PR with the prompt in the body

## Phase 3: TIL Repo
Simon keeps TIL as a separate repo: [simonw/til](https://github.com/simonw/til) (575 entries, 1,397 stars).

His TIL structure:
- One markdown file per learning, organized by topic folder (`llms/`, `docker/`, etc.)
- Auto-generated README index with dates (Python script)
- Served as searchable website via [Datasette](https://datasette.io/) at til.simonwillison.net
- Atom feed for subscribers
- Human-written, in his voice

Our TIL plan:
- [ ] Create separate `til` repo
- [ ] Organize by topic (e.g., `ai-safety/`, `openclaw/`, `hardware/`, `supply-chain/`)
- [ ] Source initial entries from Discord conversations and DMs (already have voice samples)
- [ ] Add auto-generated README index
- [ ] Consider Datasette hosting later

### Voice Source Material
Discord conversations from April 4, 2026 contain natural TIL-style observations:
- LiteLLM supply chain compromise warning
- Jensen/Simon safety framework connection
- Claude Code billing changes (token -> extra usage)
- NemoClaw + NemoTron evaluation interest
- Voice pipeline ideas (PWA on Raspberry Pi, bypassing third-party platforms)

## Phase 4: Connect Research -> Blog
- [ ] Move blog drafts into this workflow (or keep in separate kodyabbott.com repo)
- [ ] Research projects feed blog posts (like Simon's `research` -> `simonwillisonblog` pipeline)
- [ ] Cross-link: blog references research trail, research references published posts

## References

- Simon Willison's research repo: https://github.com/simonw/research
- Simon's TIL repo: https://github.com/simonw/til
- "Code research projects with async coding agents": https://simonwillison.net/2025/Nov/6/async-code-research/
- cogapp (README auto-generation): https://github.com/ned-batchelder/cog
- llm CLI tool: https://github.com/simonw/llm
- Datasette: https://datasette.io/
