# Research Notes: Jensen Huang's GTC Comments on AI Agent Safety

## Background

At NVIDIA GTC, Jensen Huang discussed AI agent safety and described a capability constraint: an AI agent should never have all three of these at the same time:

1. Write code
2. Execute code
3. Search the web

Pick two. All three together creates an uncontrolled autonomy loop -- the agent can write something, run it, pull in new information from the internet, and iterate on itself with zero human involvement.

He said it and moved on. He didn't name it.

## Research Status

### What's confirmed
- Jensen spoke at GTC about AI agent safety
- The "pick two of three" framing (write/execute/search) is attributed to him
- NVIDIA launched NemoClaw, their enterprise agent framework, which suggests they're actively thinking about agent capability constraints
- The structural argument maps to the same pattern as Simon Willison's Lethal Trifecta: no single capability is dangerous alone, it's the combination

### What still needs sourcing
- **TODO**: Find the exact GTC talk and timestamp where Jensen makes this statement
- **TODO**: Determine if this was GTC 2025 or GTC 2026
- **TODO**: Confirm whether this is a direct quote or a paraphrase that's been circulating
- **TODO**: Verify NemoClaw URL (https://developer.nvidia.com/nemoclaw) is live and accurate

### Public timeline
- Kody Abbott first posted the Jensen/Simon connection publicly in NVIDIA Developer Discord (#general-ai-discussion) on April 4, 2026: https://discord.com/channels/1019361803752456192/1340013766942789652/1490076148124618833

## Connection to Other Frameworks

Jensen's framing comes from the **builder's perspective** -- "here's what you shouldn't build." The danger is the agent doing things you didn't ask for.

Simon Willison's Lethal Trifecta comes from the **security researcher's perspective** -- "here's how you get hacked." The danger is data leaving through a channel you didn't think about.

Same structural insight, different angle. Neither has cited the other.

## GTC Keynote Sources

- **TODO**: Find verified YouTube links for GTC 2025 and GTC 2026 keynotes
- **TODO**: Identify which keynote contains the agent safety comments and find the timestamp

## Related Sources

- Simon Willison's Lethal Trifecta (Jun 16, 2025): https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/
- Simon Willison, Bay Area AI Security talk (Aug 9, 2025): https://simonwillison.net/2025/Aug/9/bay-area-ai/
- Simon Willison on Lenny's Podcast (Apr 2, 2026): https://simonwillison.net/2026/Apr/2/lennys-podcast/
- Google DeepMind CaMeL paper: https://arxiv.org/abs/2503.18813
- Design Patterns for Securing LLM Agents: https://arxiv.org/abs/2506.08837
- Google's Agent Security Framework (Jun 15, 2025): https://simonwillison.net/2025/Jun/15/ai-agent-security/
- NVIDIA NemoClaw: https://developer.nvidia.com/nemoclaw (TODO: verify URL)
