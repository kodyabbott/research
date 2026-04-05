# Research Repo -- Agent Instructions

This repo's structure and workflow is based on Simon Willison's [simonw/research](https://github.com/simonw/research).
See his post [Code research projects with async coding agents](https://simonwillison.net/2025/Nov/6/async-code-research/) for the philosophy behind this approach.

## For humans reading this

This file tells AI agents how to contribute research to this repo. If you're a person, the [README](README.md) explains what this repo is and how to read it.

## For agents

### How to do research

Start by creating a new folder for your work with an appropriate name.

Create a notes.md file in that folder and append notes to it as you work, tracking what you tried and anything you learned along the way.

Build a README.md report at the end of the investigation. Include this banner at the top of every project README, below the title:

```markdown
<!-- AI-ASSISTED-NOTE -->
> [!NOTE]
> This is an AI-assisted research report. Research was conducted collaboratively with an LLM (Claude via OpenClaw). For more information, see the [main research repository](https://github.com/kodyabbott/research).
<!-- /AI-ASSISTED-NOTE -->
```

### What "AI-assisted" means

This repo uses **AI-ASSISTED-NOTE**, not AI-GENERATED-NOTE. The distinction:
- The human directs the research, verifies claims, and controls what gets published
- The agent searches, fetches, cross-references, and drafts
- Unverified claims must be flagged as such in notes.md

### Reducing hallucinations

These rules are derived from the [Claude API: Reduce Hallucinations](https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/reduce-hallucinations) guide and the [Claude Code Best Practices](https://code.claude.com/docs/en/best-practices.md).

**Allow uncertainty:**
- If you're unsure about any claim, say "I don't have enough information to confidently assess this." Don't fill gaps with plausible-sounding information.
- For anything time-sensitive (pricing, features, versions, current events): search first, answer second.

**Ground claims in source text:**
- For tasks involving documents or web content, extract word-for-word quotes first before performing analysis. This grounds responses in actual text rather than general knowledge.
- Only base analysis on extracted quotes, not general knowledge.

**Verify with citations:**
- Every factual claim requires a source: a URL, a file path with line number, a paper citation, or an exact quote.
- After drafting, review each claim. For each claim, find a direct quote from the source that supports it. If you can't find a supporting quote, remove the claim and mark where it was with `[REMOVED -- no supporting source found]`.

**Chain-of-thought verification:**
- Explain reasoning step-by-step before giving a final answer. This reveals faulty logic or assumptions.

**External knowledge restriction:**
- When analyzing specific sources, only use information from those sources. Do not supplement with general training knowledge unless explicitly asked.

**When corrected:**
- Don't just say "good catch." Identify WHY you were wrong and WHAT you should have done instead.
- If a previous answer in the same session was wrong, explicitly correct it. Don't quietly move on.

### Commit rules

Your final commit should include just that folder and selected items from its contents:

- The notes.md and README.md files
- Any code you wrote along the way
- If you checked out and modified an existing repo, the output of "git diff" against that modified repo saved as a file -- but not a copy of the full repo
- If appropriate, any binary files you created along the way provided they are less than 2MB in size

Do NOT include full copies of code that you fetched as part of your investigation. Your final commit should include only new files you created or diffs showing changes you made to existing code.

Don't create a _summary.md file -- these are added automatically after you commit your changes.

Commit after every large step. Don't batch changes. The commit history is part of the research trail.

## Sources for these instructions

- [simonw/research AGENTS.md](https://github.com/simonw/research/blob/main/AGENTS.md) -- repo structure and commit rules
- [Code research projects with async coding agents](https://simonwillison.net/2025/Nov/6/async-code-research/) -- philosophy
- [Claude API: Reduce Hallucinations](https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/reduce-hallucinations) -- anti-hallucination techniques
- [Claude Code Best Practices](https://code.claude.com/docs/en/best-practices.md) -- CLAUDE.md guidance
- [Claude Code Memory docs](https://code.claude.com/docs/en/memory.md) -- file structure and conventions
