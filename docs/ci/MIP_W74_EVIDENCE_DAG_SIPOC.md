# CODE PURPLE W74 — Red-root evidence qualification DAG

## Authority and scope

Evidence aid for ABACUS #1860 and canonical BD/LDAB #1929.
W72 (#2347), W73 (#2351) and W74 (#2352) have disjoint writers.
Source owner: `scripts/red_root_delta.py`. Admission remains **HOLD**.

## Directed acyclic graph

```mermaid
flowchart TD
  A["01 Frozen PR base and exact head"] --> B["02 CI producers"]
  B --> C["03 Scanner logs and run identity"]
  C --> D{"04 All selected logs parsed?"}
  A --> E{"05 Valid base and stable config?"}
  D -- no --> U["08 Withhold numeric bound: null"]
  E -- no --> U
  D -- yes --> F{"06 Scanner selected?"}
  F -- no --> U
  F -- yes --> G["07 Compute touched-file bound"]
  E -- yes --> G
  G --> H["09 Qualified input evidence"]
  U --> H2["09 Record missing inputs and reason"]
  H --> I["10 Native CI and independent disposition"]
  H2 --> I
  I --> J{"11 All governance gates verified?"}
  J -- no --> K["12 HOLD: no merge/root closure"]
  J -- yes --> L["12 Independent admission review"]
  classDef src fill:#e8f1fa,stroke:#53789a,color:#19334b;
  classDef input fill:#fff3dc,stroke:#a87d38,color:#57401b;
  classDef blocked fill:#f7e4e6,stroke:#a4505c,color:#61232c;
  classDef pass fill:#e5f3e8,stroke:#588769,color:#21482b;
  class A,B,C src;
  class D,E,F,I,J input;
  class U,H2,K blocked;
  class G,H,L pass;
```

The numeric bound qualifies input data, **not** scanner exit success.
Neither full-main coverage nor engineering root closure follows.

## SIPOC

| Step | Contract |
| --- | --- |
| Supplier | Exact-head checkout and existing CI producers |
| Input | Base, head, changed paths, logs and config changes |
| Process | Normalize, parse, qualify or withhold numeric bound |
| Output | Red-root JSON and Markdown CI step summary |
| Customer | MIP controller, #1860 admission, #1929 root owner |

## Disjoint worker lanes

| Lane | Ownership | Evidence |
| --- | --- | --- |
| W72 | Cohort workflow/test | Native Python 3.10/3.12 |
| W73 | P41 CLI/tests | Blocked exit, negative tests |
| W74 | Red-root census/tests | Parsed inputs, reverse tests |
| Owner | Ruleset/review | RED canary, required checks |

## SPINE / SPLINE

`N0 source -> N1 log completeness -> N2 candidate tests`
`-> N3 native jobs/artifacts -> N4 security/review`
`-> N5 independent root disposition`.

A valid zero is scoped to selected parsed input populations.
Missing logs, PR base, configuration stability or scanner selection
produce `null`, never a fabricated clean result.

Stop on base drift, missing log, incomplete scanner evidence,
native failure, unresolved security or absent independent review.
Never dispatch CODEX mutation or merge based on this diagram.
