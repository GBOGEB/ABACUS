# DOW Architecture W57

## High-level architecture

```text
GOVERNED PAYLOAD
      |
      v
INGRESS GATE
      |
      v
ORCHESTRATOR
  +---+---+
  v   v   v
Agents MCP Runners
  |    |    |
  +----+----+
       |
 +-----+-----+-----+
 v     v     v     v
DMAIC  PCA   BT    QA/Render
  \     |     |     /
   \    |     |    /
      RUNTIME GRAPH
           |
           v
       TELEMETRY
           |
           v
       DOW RECEIPT
```

## cADR
See `DOW_cADR_W57.yaml`.

## xOCD
See `DOW_xOCD_W57.yaml`.

## User-facing outward family
- DOW_ARCHITECTURE.xlsx
- DOW_ARCHITECTURE.html
- DOW_ARCHITECTURE.pptx
- DOW_ARCHITECTURE.pdf
- DOW_AGENT_REGISTER.xlsx
- DOW_RUNTIME_GRAPH.html
- DOW_PIPELINE.html
- DOW_DMAIC_SCORECARD.xlsx
- DOW_PCA_BT_REPORT.pdf
- DOW_TELEMETRY.html

## Interaction role
B2 receives governed execution payload from CODEX/KEB. Runtime workers execute analysis and QA without mutating engineering truth. B3 returns a digest-bound DOW receipt to cryoplant-project for child disposition.

## Boundary
ABACUS owns orchestration, runtime, analysis, telemetry and render QA. It does not own QPS engineering truth or KEB semantic policy.
