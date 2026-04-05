# Research Repo -- Agent Instructions

Based on Simon Willison's [simonw/research](https://github.com/simonw/research).
See [Code research projects with async coding agents](https://simonwillison.net/2025/Nov/6/async-code-research/).

For humans: see [README.md](README.md).

## How to do research

1. Create a new folder with an appropriate name
2. Create `notes.md` -- running log of what you tried and learned
3. Build `README.md` -- polished report with the AI-ASSISTED-NOTE banner (template below)
4. Follow the workflow and source rules in `.claude/rules/`
5. Commit after every large step -- the git history is part of the research trail

### README banner template

```markdown
<!-- AI-ASSISTED-NOTE -->
> [!NOTE]
> This is an AI-assisted research report. Research was conducted collaboratively using Claude Code (Anthropic, Opus 4.6). For more information, see the [main research repository](https://github.com/kodyabbott/research).
<!-- /AI-ASSISTED-NOTE -->
```

**AI-ASSISTED** (not AI-GENERATED): human directs and verifies, agent searches and drafts.

## Commit rules

Include only the project folder with: notes.md, README.md, code you wrote, diffs of modified repos (not full copies), and binary files under 2MB. Don't create `_summary.md` files.

## .claude/ directory

- `.claude/settings.json` -- project permissions and model config
- `.claude/rules/` -- auto-loaded every session: research workflow, source verification rules
- `.claude/agents/` -- spawnable agents: researcher, source-verifier, adversarial-reviewer, url-auditor

## Sources

- [simonw/research AGENTS.md](https://github.com/simonw/research/blob/main/AGENTS.md)
- [Claude API: Reduce Hallucinations](https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/reduce-hallucinations)
- [Claude Code Best Practices](https://code.claude.com/docs/en/best-practices.md)
- [Claude Code Memory docs](https://code.claude.com/docs/en/memory.md)
