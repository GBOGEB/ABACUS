# STAKEHOLDER_ROUTING.md — Distribution Logic

> **Version:** 1.0.0  
> **References:** RULE-150 through RULE-153 (RENDER_RULES.md)

---

## Overview

GBOGEB/ABACUS routes generated outputs to different stakeholder groups based on distribution tags embedded in each slide's semantic card. This ensures the right content reaches the right audience automatically.

---

## Distribution Tags

| Tag | Target | Content Type |
|-----|--------|--------------|
| `[KEB]` | Executive / Strategic Team | Executive summaries, high-level architecture views, decision frameworks, KPIs |
| `[DOW]` | Technical / Implementation Team | Detailed specifications, implementation guides, API references, code samples |
| `[ALL]` | All Stakeholders | Cross-cutting content, announcements, shared references |

---

## Routing Rules

### Rule 1: Tag Assignment
Every slide or page **must** have at least one routing tag in its semantic card:

```yaml
---
slide_id: arch-overview-001
purpose: "Present system architecture at 10,000ft level"
audience: "Executive stakeholders"
routing:
  - KEB
---
```

### Rule 2: Multi-Tag Content
Content may be tagged for multiple audiences:

```yaml
routing:
  - KEB
  - DOW
```

This generates separate output artifacts optimized for each audience.

### Rule 3: Default Routing
- If no routing tag is specified, content defaults to `[ALL]`
- `[ALL]` content is included in every distribution package

### Rule 4: Content Adaptation

| Aspect | `[KEB]` | `[DOW]` |
|--------|---------|---------|
| Detail Level | Summary / highlights | Full technical detail |
| Visualizations | Charts, KPIs, trends | Architecture diagrams, data flows |
| Language | Business terminology | Technical terminology |
| Slide Count | Condensed (≤15 slides) | Comprehensive (no limit) |
| Speaker Notes | Executive talking points | Implementation notes |

---

## Routing Pipeline

```
Source Content (CODEX)
       │
       ▼
┌─────────────────────┐
│  Semantic Card Parse │  ← Extract routing tags
└──────────┬──────────┘
           │
     ┌─────┴──────┐
     ▼             ▼
┌─────────┐  ┌─────────┐
│  [KEB]  │  │  [DOW]  │
│ Package │  │ Package │
└────┬────┘  └────┬────┘
     │             │
     ▼             ▼
  Executive     Technical
  Distribution  Distribution
```

## Implementation

Routing metadata is:
1. **Defined** in the semantic card of each slide (YAML front matter)
2. **Validated** by `RENDER_LINTER.py` (semantic_card_required rule)
3. **Tracked** in `lineage_manifest.json` (stakeholder_routing field)
4. **Enforced** via CI/CD — PRs without routing tags trigger warnings

## Manifest Integration

Each lineage record includes routing information:

```json
{
  "slide_id": "arch-overview-001",
  "stakeholder_routing": ["KEB"],
  "derived_from": "themes/engineering/slides/architecture.yaml",
  "generated_outputs": [
    {"format": "html", "path": "_site/keb/arch-overview-001.html"},
    {"format": "pdf", "path": "output/keb/architecture-summary.pdf"}
  ]
}
```
