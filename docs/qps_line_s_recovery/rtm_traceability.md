# RTM Traceability Map

Status: draft MDA traceability. This file is an initial Agent-A-ready scaffold.

| Requirement | Interpretation for MDA | Model evidence | Current status |
|---|---|---|---|
| RTM-260 | Credited abnormal recovery shall not lose more than 1 percent helium inventory. | Applicant package requires no relief opening for credited no-loss cases; future runner shall integrate lost mass. | STARTED |
| RTM-261 | QPS shall cope with Line S / QRB.S return flow: 100 g/s abnormal and 200 g/s normal/peak context. | Scenario matrix covers 100, 112, 150, and 200 g/s cases over V_eff band. | STARTED |
| RTM-262 | QPS shall recover normal helium circulation after abnormal event is resolved. | Recovery path and HP start logic still open; requires procedure evidence. | OPEN_RFI |
| RTM-292 | Related Line S or recovery interface pressure build-up requirement. | P_LIMIT register created; final pressure answer gated until limits are supplied. | OPEN_RFI |
| OFFER-22 | Applicant shall present recovery strategy and maximum flow that QPS can accept from Line S. | Applicant response package requires V_eff, P_LIMIT, recovery power, HP capacity, and flow profiles. | STARTED |

## Current evidence files

- `docs/qps_line_s_recovery/applicant_response_package.md`
- `docs/qps_line_s_recovery/assumptions_register.yaml`
- `docs/qps_line_s_recovery/p_limit_register.md`
- `docs/qps_line_s_recovery/generated/scenario_matrix.md`
- `models/qps_line_s/line_s_buffer.py`
- `tests/test_line_s_buffer.py`

## Open traceability gaps

1. Confirm exact RTM-292 wording.
2. Confirm Line S pressure-envelope values.
3. Confirm whether recovery compressors are on credited backup power during LOOP.
4. Confirm basis for 112 g/s pre-HP inflow.
5. Confirm HP acceptance capacity and suction envelope.
