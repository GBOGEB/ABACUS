# RENDER_TEST_SUITE.md — Comprehensive Test Scenarios

> **Version:** 1.0.0  
> **Coverage:** All RENDER_RULES.md rules  
> **Automation:** `pytest tests/` or `python -m pytest tests/ -v`

---

## §1 Layout Governance Tests

### 1.1 Overflow Prevention (RULE-010, RULE-011, RULE-012)

| Test ID | Description | Input | Expected Result |
|---------|-------------|-------|-----------------|
| LAY-001 | Line exceeding 200 chars triggers warning | 250-char line in .md | WARNING: no_overflow |
| LAY-002 | `overflow: hidden` CSS is blocked | CSS with overflow:hidden | ERROR: no_overflow |
| LAY-003 | Normal content passes without findings | Standard 80-char lines | No findings |
| LAY-004 | Figure below 60% scale triggers error | Figure with min_scale violation | ERROR: scale_minimum |

### 1.2 Spacing (RULE-020, RULE-021, RULE-022)

| Test ID | Description | Input | Expected Result |
|---------|-------------|-------|-----------------|
| LAY-010 | Content block gap ≥16px | Layout with 12px gap | ERROR: minimum_gap |
| LAY-011 | Section break ≥32px | Section with 24px break | ERROR: section_break |
| LAY-012 | Valid spacing passes | Compliant layout | No findings |

---

## §2 Typography Tests

### 2.1 Heading Hierarchy (RULE-030, RULE-031, RULE-032)

| Test ID | Description | Input | Expected Result |
|---------|-------------|-------|-----------------|
| TYP-001 | Sequential headings pass | H1 → H2 → H3 | No findings |
| TYP-002 | Skipped heading level detected | H1 → H3 (skipping H2) | ERROR: stable_heading_hierarchy |
| TYP-003 | Multiple H1s flagged | Two H1 headings | INFO: multiple_h1 |
| TYP-004 | Orphan heading detected | H2 with no following content | WARNING |

### 2.2 Font Size Constraints (RULE-040–RULE-052)

| Test ID | Description | Input | Expected Result |
|---------|-------------|-------|-----------------|
| TYP-010 | Body text ≥16px screen | 14px body text | ERROR: min_body_size |
| TYP-011 | Heading ≤48px screen | 56px heading | ERROR: max_heading_size |
| TYP-012 | Font ≥12px at all viewports | 10px at mobile | ERROR: min_font_size |

---

## §3 Contrast Tests

### 3.1 WCAG AA Compliance (RULE-060, RULE-061, RULE-062)

| Test ID | Description | Input | Expected Result |
|---------|-------------|-------|-----------------|
| CTR-001 | Black on white passes (21:1) | fg:#000 bg:#FFF | PASS (ratio: 21:1) |
| CTR-002 | Light gray on white fails | fg:#CCC bg:#FFF | FAIL (ratio: ~1.6:1) |
| CTR-003 | Dark gray on white passes | fg:#333 bg:#FFF | PASS (ratio: ~12.6:1) |
| CTR-004 | Large text at 3:1 passes | 24px fg:#666 bg:#FFF | PASS (ratio: ~5.7:1) |
| CTR-005 | Theme light mode validation | SEMANTIC_THEME.yaml light | All pairs ≥4.5:1 |
| CTR-006 | Theme dark mode validation | SEMANTIC_THEME.yaml dark | All pairs ≥4.5:1 |
| CTR-007 | High contrast mode validation | SEMANTIC_THEME.yaml high_contrast | All pairs ≥7:1 |

---

## §4 Content Integrity Tests

### 4.1 Orphan Bullets (RULE-080, RULE-081)

| Test ID | Description | Input | Expected Result |
|---------|-------------|-------|-----------------|
| CNT-001 | Single bullet item flagged | `- Only item` | WARNING: no_orphan_bullets |
| CNT-002 | Two+ bullet items pass | `- Item 1\n- Item 2` | No findings |
| CNT-003 | Single numbered item flagged | `1. Only item` | WARNING: no_orphan_bullets |
| CNT-004 | Nested list depth >3 flagged | 4-level nested list | WARNING: max_nesting |

### 4.2 Figure References (RULE-090, RULE-091)

| Test ID | Description | Input | Expected Result |
|---------|-------------|-------|-----------------|
| CNT-010 | Defined and referenced figure passes | Fig with ref in text | No findings |
| CNT-011 | Defined but unreferenced figure | Fig without text ref | WARNING |
| CNT-012 | Referenced but undefined figure | Text ref without fig | ERROR |

### 4.3 Speaker Notes (RULE-100)

| Test ID | Description | Input | Expected Result |
|---------|-------------|-------|-----------------|
| CNT-020 | Notes ≥50 chars passes | 60-char speaker notes | No findings |
| CNT-021 | Notes <50 chars flagged | 30-char speaker notes | WARNING |
| CNT-022 | Missing notes on slide file | No speaker_notes field | WARNING |

### 4.4 Semantic Cards (RULE-101, RULE-102)

| Test ID | Description | Input | Expected Result |
|---------|-------------|-------|-----------------|
| CNT-030 | Complete semantic card passes | slide_id + purpose + audience | No findings |
| CNT-031 | Missing slide_id | purpose + audience only | ERROR |
| CNT-032 | Missing purpose | slide_id + audience only | ERROR |
| CNT-033 | No front matter on slide | Slide file without YAML | ERROR |

---

## §5 Slide ID Tests

### 5.1 ID Format (RULE-110, RULE-111)

| Test ID | Description | Input | Expected Result |
|---------|-------------|-------|-----------------|
| SID-001 | Valid ID passes | arch-overview-001 | VALID |
| SID-002 | Missing sequence fails | arch-overview | INVALID |
| SID-003 | Non-numeric sequence fails | arch-overview-abc | INVALID |
| SID-004 | Empty string fails | "" | INVALID |
| SID-005 | Special characters fail | arch/overview-001 | INVALID |
| SID-006 | Single segment fails | architecture | INVALID |

### 5.2 Uniqueness (RULE-111)

| Test ID | Description | Input | Expected Result |
|---------|-------------|-------|-----------------|
| SID-010 | Unique IDs pass | All distinct IDs | No violations |
| SID-011 | Duplicate IDs flagged | Same ID in two files | ERROR: duplicate |

---

## §6 Lineage Tests

### 6.1 Verification Hook (Input_Master/ Processing)

| Test ID | Description | Input | Expected Result |
|---------|-------------|-------|-----------------|
| LIN-001 | Binary file creates .mock | test.pptx in Input_Master/ | .mock sidecar created |
| LIN-002 | SHA256 hash computed | Any binary file | Valid 64-char hex hash |
| LIN-003 | Manifest updated | New file processed | lineage_manifest.json updated |
| LIN-004 | Duplicate file detected | Same file re-dropped | Existing entry updated |
| LIN-005 | Invalid file rejected | Corrupted binary | Error logged, no .mock |

### 6.2 Manifest Integrity

| Test ID | Description | Input | Expected Result |
|---------|-------------|-------|-----------------|
| LIN-010 | Valid manifest schema | Correct JSON structure | Schema validation passes |
| LIN-011 | Missing required field | Record without sha256 | Schema validation fails |
| LIN-012 | Invalid timestamp format | Non-ISO-8601 date | Schema validation fails |

---

## §7 Integration Tests

### 7.1 End-to-End Pipeline

| Test ID | Description | Steps | Expected Result |
|---------|-------------|-------|-----------------|
| INT-001 | Full asset ingestion | Drop binary → verify → check manifest | Complete lineage chain |
| INT-002 | Linter + Enforcer combo | Lint then enforce slide IDs | Both pass on valid content |
| INT-003 | Theme contrast full check | Load theme → check all pairs | All AA requirements met |

### 7.2 CI/CD Workflow

| Test ID | Description | Trigger | Expected Result |
|---------|-------------|---------|-----------------|
| INT-010 | PR governance check | PR to main | All validators run |
| INT-011 | Asset verification on push | Push to Input_Master/ | Verification hook executes |
| INT-012 | Lint failure blocks merge | PR with linter errors | Check status: failure |

---

## §8 Test Execution

```bash
# Run all unit tests
python -m pytest tests/ -v

# Run specific test module
python -m pytest tests/test_render_linter.py -v

# Run with coverage
python -m pytest tests/ --cov=engines --cov-report=html

# Run integration tests only
python -m pytest tests/ -v -m integration

# Run linter directly
python engines/RENDER_LINTER.py docs/

# Run contrast checker
python engines/WCAG_CONTRAST_CHECKER.py --theme engines/SEMANTIC_THEME.yaml

# Run slide ID enforcer
python engines/SLIDE_ID_ENFORCER.py docs/

# Run verification hook
python engines/verification_hook.py --input-dir Input_Master/ --data-dir _data/
```
