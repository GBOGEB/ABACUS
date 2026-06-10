# W006 — Design ↔ As-Drawn Cross-Map Report

> Turns the W005 *0 % exact-overlap* finding into a functional, confidence-scored bidirectional cross-map. **Heuristic, not a spatial match** — the design register has no drawing coordinates, so pairs are inferred from TYPE + circuit/temperature band + within-group ordering. No HIGH-confidence pair is fabricated.

## 1. Executive summary

| Metric | Value |
| --- | --- |
| Design tags (total) | 97 |
| As-drawn real tags (total) | 141 |
| **Mapped design tags** | **43 (44.3%)** |
| – HIGH confidence (≥0.80) | 0 |
| – MEDIUM confidence (0.50–0.79) | 39 |
| – LOW confidence (0.30–0.49) | 4 |
| Unmapped design tags | 54 |
| As-drawn instances left unclaimed | 98 |
| Engineering-confirmed seeds | 0 |

## 2. Method & scoring

Type-partitioned (TYPE is a hard gate). Score per candidate pair:

| Feature | Weight | Source (design / as-drawn) |
| --- | --- | --- |
| TYPE / ISA prefix | gate | prefix / prefix |
| Circuit / temperature band | 0.45 | hundreds-digit + location text / colour-class line |
| Within-group sequence order | 0.30 | tag-number rank / tag-number rank |
| Signal / role consistency | 0.25 | 4-20mA·IO / role |

Tiers: **HIGH ≥ 0.80**, **MEDIUM 0.50–0.79**, **LOW 0.30–0.49**; below 0.30 the design tag is left **UNMAPPED** rather than asserting a weak pairing. A greedy one-to-one assignment within each TYPE prevents double-claiming an as-drawn instance.

## 3. HIGH-confidence matches (≥ 0.80)

_None._ With no drawing coordinates on the design side and no engineering-confirmed seeds yet, the order heuristic alone rarely clears 0.80. This is reported honestly rather than inflated.

## 4. MEDIUM-confidence matches (0.50–0.79)

| Design | As-drawn | Conf. | Band | Reasons |
| --- | --- | --- | --- | --- |
| CV001 | CV560 | 0.75 | 40K | TYPE_MATCH, CIRCUIT_MATCH(40K), ORDER_MATCH(#0/3) |
| CV002 | CV500 | 0.75 | 4.5K | TYPE_MATCH, CIRCUIT_MATCH(4.5K), ORDER_MATCH(#0/4) |
| CV003 | CV539 | 0.75 | WATER | TYPE_MATCH, CIRCUIT_MATCH(WATER), ORDER_MATCH(#0/2) |
| CV004 | CV549 | 0.75 | WATER | TYPE_MATCH, CIRCUIT_MATCH(WATER), ORDER_MATCH(#1/2) |
| CV100 | CV571 | 0.75 | 40K | TYPE_MATCH, CIRCUIT_MATCH(40K), ORDER_MATCH(#1/3) |
| CV101 | CV589 | 0.75 | 40K | TYPE_MATCH, CIRCUIT_MATCH(40K), ORDER_MATCH(#2/3) |
| CV200 | CV501 | 0.75 | 4.5K | TYPE_MATCH, CIRCUIT_MATCH(4.5K), ORDER_MATCH(#1/4) |
| CV201 | CV551 | 0.75 | 4.5K | TYPE_MATCH, CIRCUIT_MATCH(4.5K), ORDER_MATCH(#2/4) |
| PT300 | PT560 | 0.75 | 2K | TYPE_MATCH, CIRCUIT_MATCH(2K), ORDER_MATCH(#0/2) |
| PT301 | PT561 | 0.75 | 2K | TYPE_MATCH, CIRCUIT_MATCH(2K), ORDER_MATCH(#1/2) |
| TT003 | TT500 | 0.75 | WATER | TYPE_MATCH, CIRCUIT_MATCH(WATER), ORDER_MATCH(#0/4) |
| TT004 | TT535 | 0.75 | WATER | TYPE_MATCH, CIRCUIT_MATCH(WATER), ORDER_MATCH(#1/4) |
| TT005 | TT537 | 0.75 | WATER | TYPE_MATCH, CIRCUIT_MATCH(WATER), ORDER_MATCH(#2/4) |
| TT006 | TT547 | 0.75 | WATER | TYPE_MATCH, CIRCUIT_MATCH(WATER), ORDER_MATCH(#3/4) |
| TT100 | TT509 | 0.75 | 40K | TYPE_MATCH, CIRCUIT_MATCH(40K), ORDER_MATCH(#0/12) |
| TT101 | TT510 | 0.75 | 40K | TYPE_MATCH, CIRCUIT_MATCH(40K), ORDER_MATCH(#1/12) |
| TT102 | TT511 | 0.75 | 40K | TYPE_MATCH, CIRCUIT_MATCH(40K), ORDER_MATCH(#2/12) |
| TT103 | TT512 | 0.75 | 40K | TYPE_MATCH, CIRCUIT_MATCH(40K), ORDER_MATCH(#3/12) |
| TT104 | TT515 | 0.75 | 40K | TYPE_MATCH, CIRCUIT_MATCH(40K), ORDER_MATCH(#4/12) |
| TT105 | TT516 | 0.75 | 40K | TYPE_MATCH, CIRCUIT_MATCH(40K), ORDER_MATCH(#5/12) |
| TT106 | TT517 | 0.75 | 40K | TYPE_MATCH, CIRCUIT_MATCH(40K), ORDER_MATCH(#6/12) |
| TT107 | TT518 | 0.75 | 40K | TYPE_MATCH, CIRCUIT_MATCH(40K), ORDER_MATCH(#7/12) |
| TT108 | TT519 | 0.75 | 40K | TYPE_MATCH, CIRCUIT_MATCH(40K), ORDER_MATCH(#8/12) |
| TT109 | TT520 | 0.75 | 40K | TYPE_MATCH, CIRCUIT_MATCH(40K), ORDER_MATCH(#9/12) |
| TT110 | TT521 | 0.75 | 40K | TYPE_MATCH, CIRCUIT_MATCH(40K), ORDER_MATCH(#10/12) |
| TT111 | TT522 | 0.75 | 40K | TYPE_MATCH, CIRCUIT_MATCH(40K), ORDER_MATCH(#11/12) |
| TT200 | TT526 | 0.75 | 4.5K | TYPE_MATCH, CIRCUIT_MATCH(4.5K), ORDER_MATCH(#0/8) |
| TT201 | TT551 | 0.75 | 4.5K | TYPE_MATCH, CIRCUIT_MATCH(4.5K), ORDER_MATCH(#1/8) |
| TT202 | TT557 | 0.75 | 4.5K | TYPE_MATCH, CIRCUIT_MATCH(4.5K), ORDER_MATCH(#2/8) |
| TT203 | TT559 | 0.75 | 4.5K | TYPE_MATCH, CIRCUIT_MATCH(4.5K), ORDER_MATCH(#3/8) |
| TT204 | TT567 | 0.75 | 4.5K | TYPE_MATCH, CIRCUIT_MATCH(4.5K), ORDER_MATCH(#4/8) |
| TT300 | TT538 | 0.75 | 2K | TYPE_MATCH, CIRCUIT_MATCH(2K), ORDER_MATCH(#0/11) |
| TT301 | TT550 | 0.75 | 2K | TYPE_MATCH, CIRCUIT_MATCH(2K), ORDER_MATCH(#1/11) |
| TT302 | TT556 | 0.75 | 2K | TYPE_MATCH, CIRCUIT_MATCH(2K), ORDER_MATCH(#2/11) |
| TT303 | TT558 | 0.75 | 2K | TYPE_MATCH, CIRCUIT_MATCH(2K), ORDER_MATCH(#3/11) |
| TT304 | TT561 | 0.75 | 2K | TYPE_MATCH, CIRCUIT_MATCH(2K), ORDER_MATCH(#4/11) |
| TT305 | TT566 | 0.75 | 2K | TYPE_MATCH, CIRCUIT_MATCH(2K), ORDER_MATCH(#5/11) |
| TT306 | TT568 | 0.75 | 2K | TYPE_MATCH, CIRCUIT_MATCH(2K), ORDER_MATCH(#6/11) |
| TT307 | TT569 | 0.75 | 2K | TYPE_MATCH, CIRCUIT_MATCH(2K), ORDER_MATCH(#7/11) |

## 5. LOW-confidence matches (0.30–0.49) — needs review

| Design | As-drawn | Conf. | Band | Reasons |
| --- | --- | --- | --- | --- |
| CV300 | CV569 | 0.45 | 2K | TYPE_MATCH, CIRCUIT_MATCH(2K), ORDER_TRIVIAL(bucket<=1) |
| EH300 | EH558 | 0.45 | 2K | TYPE_MATCH, CIRCUIT_MATCH(2K), ORDER_TRIVIAL(bucket<=1) |
| PT100 | PT570 | 0.45 | 40K | TYPE_MATCH, CIRCUIT_MATCH(40K), ORDER_TRIVIAL(bucket<=1) |
| PT200 | PT501 | 0.45 | 4.5K | TYPE_MATCH, CIRCUIT_MATCH(4.5K), ORDER_TRIVIAL(bucket<=1) |

## 6. Unmapped design tags (54)

| Design | Type | Band | Reason |
| --- | --- | --- | --- |
| V001 | V | ROOM | no as-drawn instance of TYPE V |
| V002 | V | ROOM | no as-drawn instance of TYPE V |
| V003 | V | ROOM | no as-drawn instance of TYPE V |
| CV202 | CV | 4.5K | no candidate >= floor (0.30) of TYPE CV |
| CV301 | CV | 2K | no candidate >= floor (0.30) of TYPE CV |
| CV302 | CV | 2K | no candidate >= floor (0.30) of TYPE CV |
| FV001 | FV | 40K | no as-drawn instance of TYPE FV |
| FV002 | FV | 4.5K | no as-drawn instance of TYPE FV |
| FV100 | FV | 40K | no as-drawn instance of TYPE FV |
| FV200 | FV | 4.5K | no as-drawn instance of TYPE FV |
| FV003 | FV | 2K | no as-drawn instance of TYPE FV |
| FV004 | FV | VACUUM | no as-drawn instance of TYPE FV |
| FV005 | FV | VACUUM | no as-drawn instance of TYPE FV |
| FV006 | FV | VACUUM | no as-drawn instance of TYPE FV |
| FV300 | FV | 2K | no as-drawn instance of TYPE FV |
| HV001 | HV | ROOM | no candidate >= floor (0.30) of TYPE HV |
| HV002 | HV | ROOM | no candidate >= floor (0.30) of TYPE HV |
| HV006 | HV | ROOM | no candidate >= floor (0.30) of TYPE HV |
| HV003 | HV | ROOM | no candidate >= floor (0.30) of TYPE HV |
| HV004 | HV | ROOM | no candidate >= floor (0.30) of TYPE HV |
| HV005 | HV | ROOM | no candidate >= floor (0.30) of TYPE HV |
| PT001 | PT | ROOM | no candidate >= floor (0.30) of TYPE PT |
| PT002 | PT | ROOM | no candidate >= floor (0.30) of TYPE PT |
| PT003 | PT | ROOM | no candidate >= floor (0.30) of TYPE PT |
| PT004 | PT | ROOM | no candidate >= floor (0.30) of TYPE PT |
| PT005 | PT | WATER | no candidate >= floor (0.30) of TYPE PT |
| PV001 | PV | ROOM | no as-drawn instance of TYPE PV |
| SV001 | SV | VACUUM | no as-drawn instance of TYPE SV |
| SV002 | SV | VACUUM | no as-drawn instance of TYPE SV |
| SV100 | SV | 40K | no as-drawn instance of TYPE SV |
| SV200 | SV | 4.5K | no as-drawn instance of TYPE SV |
| SV003 | SV | ROOM | no as-drawn instance of TYPE SV |
| SV300 | SV | 2K | no as-drawn instance of TYPE SV |
| HX300 | HX | 2K | no as-drawn instance of TYPE HX |
| TT001 | TT | ROOM | no candidate >= floor (0.30) of TYPE TT |
| TT002 | TT | ROOM | no candidate >= floor (0.30) of TYPE TT |
| TT205 | TT | 4.5K | no candidate >= floor (0.30) of TYPE TT |
| TT206 | TT | 4.5K | no candidate >= floor (0.30) of TYPE TT |
| TT207 | TT | 4.5K | no candidate >= floor (0.30) of TYPE TT |
| TT308 | TT | 2K | no candidate >= floor (0.30) of TYPE TT |
| TT309 | TT | 2K | no candidate >= floor (0.30) of TYPE TT |
| TT310 | TT | 2K | no candidate >= floor (0.30) of TYPE TT |
| J001 | J | ROOM | no as-drawn instance of TYPE J |
| EH001 | EH | ROOM | no candidate >= floor (0.30) of TYPE EH |
| EH002 | EH | ROOM | no candidate >= floor (0.30) of TYPE EH |
| EH301 | EH | 2K | no candidate >= floor (0.30) of TYPE EH |
| EH302 | EH | 2K | no candidate >= floor (0.30) of TYPE EH |
| EH303 | EH | 2K | no candidate >= floor (0.30) of TYPE EH |
| FT001 | FT | WATER | no as-drawn instance of TYPE FT |
| FT002 | FT | WATER | no as-drawn instance of TYPE FT |
| LE300 | LE | 2K | no as-drawn instance of TYPE LE |
| LI300 | LI | 2K | no as-drawn instance of TYPE LI |
| RD300 | RD | 2K | no as-drawn instance of TYPE RD |
| RD301 | RD | 2K | no as-drawn instance of TYPE RD |

## 7. W005 PPT re-allocations (carried as annotations)

These are TYPE re-assignments documented in the QM instrumentation deck — **not** design↔as-drawn identities — recorded in `canonical_register_v2.yaml`:

| Tag | Reallocated to | Target |
| --- | --- | --- |
| TT535 | PZ | phase separator (PZ) — coldest part |
| TT525 | PZ | phase separator (PZ) — warmest part |

## 8. Recommendations

1. **Engineering review** of MEDIUM pairs to promote/demote and seed `KNOWN_SEEDS`.
2. **Investigate unmapped TYPEs** (`FV`, `FT`, `HX`, `J`, `LE`, `LI`, `PV`, `RD`, `SV`) — present in design, absent from the as-drawn catalog (drawing gap or different sheet).
3. **Add coordinates to the design register** (or a sheet/zone hint) to unlock a true spatial match and lift confidence into the HIGH tier.
4. **Re-run** after each seed confirmation: `PYTHONPATH=src python3 -m abacus_svg_pid.build_w006_crossmap`.


---
_Generated by `build_w006_crossmap.py` — regenerable via `./make.sh`._
