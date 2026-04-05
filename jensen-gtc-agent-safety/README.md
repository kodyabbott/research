# Jensen Huang's GTC Comments on AI Agent Capability Constraints

<!-- AI-ASSISTED-NOTE -->
> [!NOTE]
> This is an AI-assisted research report. Research was conducted collaboratively with an LLM (Claude via OpenClaw). For more information, see the [main research repository](https://github.com/kodyabbott/research).
<!-- /AI-ASSISTED-NOTE -->

## Summary

At NVIDIA GTC, CEO Jensen Huang described a rule for AI agent safety: an agent should never simultaneously have the ability to (1) write code, (2) execute code, and (3) search the web. Any two is manageable. All three creates an uncontrolled autonomy loop where the agent can recursively self-improve with no human checkpoint.

He didn't name it. He said it and moved on.

## The Framework

| Capability | Alone | Risk When Combined |
|-----------|-------|-------------------|
| Write code | Safe | Agent can create arbitrary programs |
| Execute code | Safe | Agent can run what it writes |
| Search the web | Safe | Agent can pull in new information and iterate |

**All three together**: write + execute + search = the agent can author code, run it, learn from the internet how to do it better, and repeat -- with no human in the loop.

## Why This Matters

This is the same structural argument that Simon Willison makes with the [Lethal Trifecta](https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/), but from the opposite direction:

- **Jensen (builder's perspective)**: Here's what you shouldn't build. The risk is uncontrolled autonomy.
- **Simon (security researcher's perspective)**: Here's how you get hacked. The risk is data exfiltration via prompt injection.

Both say: no single capability is dangerous alone. It's the combination. Constrain at least one leg.

## Open Questions

- The exact GTC talk and timestamp need to be sourced -- see [notes.md](notes.md)
- This framework doesn't have a name yet. Simon's has "Lethal Trifecta." Jensen's is unnamed.
- How does NVIDIA's own NemoClaw framework implement these constraints in practice?

## Sources

- NVIDIA GTC keynote (TODO: identify year and timestamp) -- see [notes.md](notes.md)
- Simon Willison, "The Lethal Trifecta" (Jun 16, 2025): https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/
- Simon Willison, Bay Area AI Security Meetup talk (Aug 9, 2025): https://simonwillison.net/2025/Aug/9/bay-area-ai/
- Simon Willison on Lenny's Podcast (Apr 2, 2026): https://simonwillison.net/2026/Apr/2/lennys-podcast/
- Google DeepMind, "Defeating Prompt Injections by Design" (CaMeL): https://arxiv.org/abs/2503.18813
- "Design Patterns for Securing LLM Agents against Prompt Injection": https://arxiv.org/abs/2506.08837
- Google, "An Introduction to AI Agent Security": https://simonwillison.net/2025/Jun/15/ai-agent-security/
