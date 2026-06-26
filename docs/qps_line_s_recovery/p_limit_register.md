# P_LIMIT Register

Status: OPEN_RFI. This register prevents publication of a false single allowed pressure build-up value.

## Governing expression

```text
P_LIMIT = min(
  design pressure,
  maximum operating pressure,
  relief set pressure minus margin,
  recovery-compressor suction maximum,
  HP-compressor suction maximum,
  interface maximum
)
```

## Required Applicant confirmations

| Component | Value | Unit | Status | Required from |
|---|---:|---|---|---|
| design pressure | TBD | bar | OPEN_RFI | Applicant |
| maximum operating pressure | TBD | bar | OPEN_RFI | Applicant |
| relief set pressure minus margin | TBD | bar | OPEN_RFI | Applicant |
| recovery-compressor suction maximum | TBD | bar | OPEN_RFI | Applicant |
| HP-compressor suction maximum | TBD | bar | OPEN_RFI | Applicant |
| interface maximum | TBD | bar | OPEN_RFI | Applicant |

## Release rule

A fixed pressure build-up answer is not allowed until P_LIMIT and V_EFF are resolved. Until then the answer remains:

```text
Delta_P_allowed = P_LIMIT - P_initial

t_available = Delta_P_allowed / dPdt
```
