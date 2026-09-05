# W53/P05K1 — Deep strict TS residual validation wave

## Mission
Promote the strongest P05J result into the first governed QPLANT strict numerical residual, or name the exact blocker without granting artificial credit.

## Exact evidence boundary
Current ALAT source: `C1462-TN-001_0_SCK_CEN_MYRRHA_Phase_1_Technical_Proposal`.
Controlled child locators: guaranteed performance p55/81 §3; guaranteed conditions p56/81; non-binding thermodynamic example inputs p59/81; outputs p60/81.

Exact current-offer non-binding TS example:

| quantity | D | E |
|---|---:|---:|
| P | 14.12 bara | 13.12 bara |
| T | 35 K | 55 K |
| h bidder | 196438 J/kg | 302915 J/kg |
| s bidder | 14861 J/kg/K | 17428 J/kg/K |

`QTS=8200 W`; reconstructed bidder-example flow `77.01 g/s`.
Contract independently carries Table-8 `QTS=8200 W` and Table-9 `D/E ≈77 g/s`.

Authority warning: the exact 14.12/35 -> 13.12/55 state is explicitly a current-offer **example and non-binding** state inside the guaranteed envelope. It shall not be promoted to a fixed guaranteed BOP. The reconstructed 77.01 g/s is derived from bidder Q/Δh and is not independent evidence.

## Residual battery
### R3A — cross-source energy residual
Use exact ALAT D/E P/T + contract `≈77 g/s` + governed independent properties:
`Q_pred = mdot_contract * [h(E)-h(D)]`.
Emit W and % residual against 8200 W.

### R3B — inverse-flow residual
`mdot_pred = 8200/[h(E)-h(D)]`; compare to contract ≈77 g/s.

### R3C — bidder internal consistency
`Q_bidder = 0.07701*(302915-196438)`.
Classify `NON_INDEPENDENT_SOURCE_CONSISTENCY`; never score as strict PASS.

### R3D — provider cross-validation
Evaluate exact D/E state with pinned CoolProp 7.2.0 and a genuinely independent property source: HEPAK, MBWR/Aspen-HYSYS, governed REFPROP-equivalent, or exact source table. Historical ALAT method lineage (`Aspen HYSYS v10 / MBWR / HEPAK v3.4`) is supporting lineage, not exact-state validation by itself.

## Predeclared flow sensitivity
Because Table-9 says approximately 77 g/s, calculate before disposition at 76.5, 77.0 and 77.5 g/s. Add ±1 g/s only if controlled contract semantics justify it. No post-hoc tolerance selection.

## Quantitative receipt
Emit: source SHA/locators; D/E P/T; provider/version; hD/hE/Δh; predicted duty at every flow point; W/% residual; inverse flow; flow residual; provider disagreement %; bidder internal-consistency residual; source-bound fraction; independent-reference coverage; provenance completeness; uncertainty width; retry count; PASS/DEFER/FAIL.

## Fail-closed negative tests
DEFER/FAIL if: ALAT 77.01 is called independent; non-binding state is called guaranteed; rounded 14/40 -> 13/60 substitutes for exact state; topology identity receives residual credit; CoolProp validates itself; historic pre-study overrides current offer; missing property values are imputed; tolerance is chosen after the result; parent runtime self-promotes compliance.

## DoV gate
Track strict residual PASS/DEFER/FAIL, same-boundary completeness, independent-reference coverage, provider agreement, residual W/%, flow residual, source-bound %, provenance %, diagnostic DoV delta and formal credit delta separately.

Formal credit remains zero until CODEX validation and child ACCEPT against a governed obligation.

## PCA / BT observation contribution
Add only measured features: thermo residual %, provider disagreement %, independent-reference coverage, source-bound %, provenance %, uncertainty width and execution retries. Compare BT candidates K1 TS validation, K2 Line-S repair, K3 VLP flow/KCv binding, HEPAK low-T reference and local worker buildout. Priority never equals compliance.

## Definition of Done
PASS path: exact source bound + contract ≈77 semantics governed + CoolProp receipt + independent property receipt + predeclared tolerance satisfied + CODEX PASS + child ACCEPT.

DEFER path: all computable work complete and exact missing blocker explicitly identified.

## Victory
**First genuine strict numerical residual = 1/5**, with no circular source arithmetic, post-hoc tolerance or parent self-promotion.
