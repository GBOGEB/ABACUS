# QPS Debug Global Federation — ABACUS/DOW

ABACUS/DOW consumes the CODEX/KEB QPS-debug binding and remains
fail-closed.

```text
QPS TRIAGE runtime
  -> QPS KEB envelope
  -> CODEX/KEB binding
  -> ABACUS/DOW binding
  -> child disposition
  -> QPS feedback
```

DOW can ACCEPT only when the CODEX object identifies semantic source
`CODEX/KEB`, is itself ACCEPT, carries a non-UNKNOWN producer exact SHA,
and preserves both the runtime-step and recursive-audit evidence checks.

Missing, DEFER, stale, historical-only, or malformed input remains DEFER.
DOW runtime ACCEPT never transfers engineering authority and does not modify
formal engineering or negotiation credit.
