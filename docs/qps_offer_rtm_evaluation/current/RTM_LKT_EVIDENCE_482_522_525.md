# LKT evidence reconciliation — RTM-482 and RTM-522..525

Status: **RETURNED-EVIDENCE BOUNDARY CLARIFIED — NO REQUIREMENT CLOSURE**

## Governing rule

The Owner-controlled Contract/RTM acceptance baseline is unchanged. LKT is assessed against the same baseline as ALAT.

The recovered comparison source identifies the LKT source as an **exception-only register**. For each RTM in this wave, `LKT Exception Rows = 0`. The source itself warns that no matching exception row **does not prove compliance** and shall be treated only as **no exception on file**.

Therefore the previous `NE — exact granular returned evidence still to be bound` state can be refined, but not promoted to `C`:

| RTM | LKT exception rows | Governed LKT state | Compliance inference | Required positive evidence |
|---|---:|---|---|---|
| RTM-482 | 0 | **NO EXCEPTION ON FILE** | **PROHIBITED** | Explicit LKT commissioning/test commitment covering all Owner-baseline elements, including oil-removal, dryer-capacity, vibration and CIS/control validation. |
| RTM-522 | 0 | **NO EXCEPTION ON FILE** | **PROHIBITED** | Explicit TS-SB sequence, VLP state, ≥24 h duration, return and acceptance commitment. |
| RTM-523 | 0 | **NO EXCEPTION ON FILE** | **PROHIBITED** | Explicit B/C point mapping, both ≥12 h periods, transitions/return and acceptance commitment. |
| RTM-524 | 0 | **NO EXCEPTION ON FILE** | **PROHIBITED** | Explicit ≥48 h 4K-SB run, compressor-off state, transition/start-up and acceptance commitment. |
| RTM-525 | 0 | **NO EXCEPTION ON FILE** | **PROHIBITED** | Explicit three back-to-back ≥48 h 2 K runs and full acceptance commitment. |

## Bidder comparison effect

This produces an intentionally asymmetric but evidence-correct comparison:

- **ALAT:** explicit returned deviations/suggestions exist and are dispositioned as D / D-CL / D-MATERIAL.
- **LKT:** no matching exception is present in the recovered exception-only register, but positive compliance evidence is not established by that absence.

The absence of a LKT exception shall therefore never be displayed as `OK`, `compliant`, or superior to ALAT without positive source evidence. It is a lower-information state, not a compliance result.

## Next evidence action

Recover/bind the LKT technical proposal, compliance statement, FAT/SAT strategy or other positive returned source for these five RTMs. Classify that positive evidence against the already-governed Owner baseline as C / CL / D / EQ. Until then all five remain open.

## HTML state surface

`QPS_RTM_LIVE_STATE.html` and `qps_rtm_live_state.json` expose this distinction as a read-only live/snapshot view. The HTML attempts to refresh the JSON from `main` when served online and falls back to its embedded snapshot when opened offline. Neither file is contractual authority; both are review/navigation surfaces over governed state records.
