# Adversarial Review Findings

Review conducted April 5, 2026 by Claude (via OpenClaw) before initial publish.

## Critical -- Fix Before Publishing

### 1. Jensen's actual quote is different from what the repo states

**Files:** `jensen-gtc-agent-safety/README.md`, `jensen-gtc-agent-safety/notes.md`

The repo states Jensen's three capabilities as: (1) write code, (2) execute code, (3) search the web.

Per [NewClawTimes GTC 2026 coverage](https://newclawtimes.com/articles/openclaw-enterprise-security-governance-challenges-gtc-2026-huang-mensch-chase/), Jensen's actual framing was: (1) accessing sensitive information, (2) executing code, (3) communicating with the outside world. His quote: "you should allow someone, including an AI, any two of those three things at one time, but not all at one time, unless it's the CEO."

"Write code" and "search the web" are not what Jensen said. This is a paraphrase that drifted enough to change the meaning. The repo's version strips out the data-access leg and replaces "external communication" with "web search."

**Note:** If accurate, the real quote actually strengthens the thesis -- Jensen's real three capabilities map much more closely to Simon's Lethal Trifecta than the paraphrased version does.

### 2. ThoughtWorks source doesn't say what we claim

**Files:** `simon-willison-lenny-podcast/README.md` line 37, `notes.md` lines 28-30

The repo states: "Per ThoughtWorks research: seniors get amplified, juniors get onboarding solved, but people in the middle face the most disruption."

The [ThoughtWorks article](https://www.thoughtworks.com/insights/articles/reflections-future-software-engineering-retreat) does not contain this three-tier breakdown. This is Simon's paraphrase from the podcast, not what the article says. We attributed it directly to ThoughtWorks.

### 3. 97% vs 99% discrepancy

**File:** `simon-willison-lenny-podcast/notes.md` line 37

Notes say "97% effectiveness = failing grade" but every Simon source says "99%". Agent error that wasn't caught.

### 4. Vibe coding "quotes" aren't actual quotes

**Files:** `simon-willison-lenny-podcast/README.md` line 43, `notes.md` line 41

"Go wild" and "take a step back" are formatted as direct quotes but don't appear in the [cited source](https://simonwillison.net/2025/Mar/19/vibe-coding/). These are paraphrases that should either be verified against the podcast audio or marked as paraphrases.

## Important -- Should Fix

### 5. No evidence of human verification in the repo

The README claims "I direct and verify" but notes.md files are full of TODOs and read as first-pass agent output. The repo claims AI-assisted but doesn't demonstrate the human layer. The notes don't show human course-corrections, rejected agent outputs, or explicit verification steps.

### 6. OpenClaw is never explained

Referenced in README, CLAUDE.md, and notes.md but never defined. A reader landing on this repo has no idea what OpenClaw is.

### 7. GitHub URL hardcoded before repo exists

`github.com/kodyabbott/research` appears in AI-ASSISTED-NOTE banners before confirming GitHub username or creating the repo.

### 8. Jensen/Simon "same structural insight" claim is looser than presented

Jensen's framework is about enterprise access control ("who gets to do what"). Simon's Lethal Trifecta is about attack surface ("how a malicious actor weaponizes your system"). Both describe capability combinations, but calling them "the same argument from opposite directions" overstates the mapping. A critical reader or Simon himself would push back on this.

### 9. Missing citation for "prompt injection" coinage

`simon-willison-lenny-podcast/README.md` line 18 states "coined the term 'prompt injection' in 2022" without linking to the [original September 12, 2022 blog post](https://simonwillison.net/2022/Sep/12/prompt-injection/).

## Minor

### 10. Star counts will go stale

`notes.md` cites "502 stars" and "11,523 stars" as precise numbers. Should use approximate counts or date the observation.

### 11. PLAN.md mentions DMs and billing details

The "Voice Source Material" section will be publicly visible. Content is probably fine but references "DMs" which could raise questions.

## Sources for Review

- [NewClawTimes: GTC 2026 coverage](https://newclawtimes.com/articles/openclaw-enterprise-security-governance-challenges-gtc-2026-huang-mensch-chase/)
- [ThoughtWorks: Reflections on Future of Software Engineering](https://www.thoughtworks.com/insights/articles/reflections-future-software-engineering-retreat)
- [Simon Willison: Not all AI-assisted programming is vibe coding](https://simonwillison.net/2025/Mar/19/vibe-coding/)
- [Simon Willison: How to stop AI's lethal trifecta](https://simonwillison.net/2025/Sep/26/how-to-stop-ais-lethal-trifecta/)
- [Simon Willison: Bay Area AI Security Meetup](https://simonwillison.net/2025/Aug/9/bay-area-ai/)
- [Simon Willison: Prompt injection attacks against GPT-3 (original 2022 coinage)](https://simonwillison.net/2022/Sep/12/prompt-injection/)
