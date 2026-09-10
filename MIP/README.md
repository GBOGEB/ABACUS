# MIP Rollout

MIP means Modernize, Innovate, Perpetuate.

This repo uses MIP as a repeatable self-improvement loop:

| Lane | Purpose | First executable evidence |
| --- | --- | --- |
| `repo_self_index` | Census the repo and expose real denominators. | `MIP/receipts/repo_self_index.json` |
| `repo_self_assess_debug_ldab` | Find debug, logging, diagnostics, and LDAB-style breakpoints/observability gaps. | Assessment section in the same receipt |
| `repo_self_assess_runners_mcp` | Classify Docker, runners, CI, MCP, and orchestration surfaces. | Assessment section in the same receipt |
| `repo_self_assess_codz_health_selfheal` | Identify code-health and self-heal candidates without silently changing behavior. | Assessment section in the same receipt |
| `repo_self_produce` | Promote reusable repo functionality into an implantable skill, agent, manager, or orchestrator. | Candidate list in the same receipt |

## DoD

1. The self-index runs locally with only the Python standard library.
2. The receipt records repo SHA, branch, dirty-state summary, file census, runtime surfaces, and candidate MIP lanes.
3. The next repair target is selected from the first red or missing evidence class, not from a widened backlog.
4. Produce candidates are separated from claims: a reusable skill/agent is a candidate until packaged, tested, and documented.

## DoV

MIP DoV is withheld until at least three distinct repo SHAs have receipts and one self-heal or produce candidate is proven by an executable check.

