# Research Workflow

Every research project follows this process:

1. **Find primary sources** -- fetch the actual talk, paper, or blog post. Don't trust circulating paraphrases.
2. **Extract exact quotes** -- copy verbatim text before summarizing. Ground analysis in real text.
3. **Build notes.md** -- running log with sources, quotes, TODOs for unverified claims.
4. **Build README.md** -- polished report. Only include claims that survived notes.md verification.
5. **Commit before reviewing** -- every large step gets its own commit.
6. **Run source-verifier agent** -- checks quotes and URLs against primary sources.
7. **Run url-auditor agent** -- extracts all session URLs from JSONL, flags uncited sources.
8. **Run adversarial-reviewer agent** -- tears apart the research for errors before publishing.
9. **Fix findings, commit each fix** -- don't batch. Each fix is its own commit.
