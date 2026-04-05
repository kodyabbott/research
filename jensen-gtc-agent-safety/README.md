# Jensen Huang's GTC 2026 Comments on AI Agent Capability Constraints

<!-- AI-ASSISTED-NOTE -->
> [!NOTE]
> This is an AI-assisted research report. Research was conducted collaboratively with an LLM (Claude via OpenClaw). For more information, see the [main research repository](https://github.com/kodyabbott/research).
<!-- /AI-ASSISTED-NOTE -->

## Summary

At a GTC 2026 panel in San Jose, NVIDIA CEO Jensen Huang described a rule for AI agent safety: an agent should never simultaneously have access to all three of these capabilities:

1. **Accessing sensitive information**
2. **Executing code**
3. **Communicating with the outside world**

Any two is manageable. All three creates a loop where the agent can access your data, run code against it, and send results externally with no human checkpoint.

His exact quote: *"If we want to be secure as an enterprise, you should allow someone, including an AI, any two of those three things at one time, but not all at one time, unless it's the CEO."*

He didn't name it. He said it and moved on.

## The Framework

| Capability | Alone | Risk When Combined |
|-----------|-------|-------------------|
| Access sensitive information | Safe | Agent can read your private data |
| Execute code | Safe | Agent can act on what it reads |
| Communicate externally | Safe | Agent can send data out |

**All three together**: access + execute + communicate = the agent can read your secrets, process them, and exfiltrate them -- with no human in the loop.

## Connection to Simon Willison's Lethal Trifecta

Simon Willison's [Lethal Trifecta](https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/) describes a similar capability-combination risk:

| Jensen's Three (GTC 2026) | Simon's Three (Lethal Trifecta) |
|---------------------------|-------------------------------|
| Accessing sensitive information | Access to private data |
| Executing code | Processes untrusted input |
| Communicating with the outside world | Exfiltration capability |

Two legs overlap directly (data access, external communication). The third differs: Jensen focuses on **code execution** as the amplifier, Simon focuses on **untrusted input** as the attack vector.

Both share the structural pattern: no single capability is dangerous alone, it's the combination. Constrain at least one leg. But they come from different threat models:

- **Jensen (enterprise security)**: Here's what access controls to enforce. The risk is an agent combining capabilities you didn't authorize.
- **Simon (attack surface)**: Here's how you get hacked. The risk is data exfiltration via prompt injection.

They converge on "pick two, constrain one" but they are not the same argument restated -- they address different threat models that happen to share a structural pattern.

## Open Questions

- The panel video needs to be found for exact timestamp -- see [notes.md](notes.md)
- This framework doesn't have a name yet. Simon's has "Lethal Trifecta." Jensen's is unnamed.
- How does NVIDIA's own NemoClaw framework implement these constraints in practice?

## Sources

- Jensen Huang, GTC 2026 panel (Computer Weekly via [NewClawTimes](https://newclawtimes.com/articles/openclaw-enterprise-security-governance-challenges-gtc-2026-huang-mensch-chase/))
- Simon Willison, [The Lethal Trifecta](https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/) (Jun 16, 2025)
- Simon Willison, [Bay Area AI Security Meetup talk](https://simonwillison.net/2025/Aug/9/bay-area-ai/) (Aug 9, 2025)
- Simon Willison, [Lenny's Podcast](https://simonwillison.net/2026/Apr/2/lennys-podcast/) (Apr 2, 2026)
- Google DeepMind, [Defeating Prompt Injections by Design (CaMeL)](https://arxiv.org/abs/2503.18813)
- [Design Patterns for Securing LLM Agents](https://arxiv.org/abs/2506.08837)
- Google, [An Introduction to AI Agent Security](https://simonwillison.net/2025/Jun/15/ai-agent-security/)
