# Exact-source delivery consumer

This read-only ABACUS DOW adapter consumes CODEX's FED-PCA-20260912-R1
register at `3bfda0e50d2e89b12d850a98f2929e73a3f3c234`.
The reviewed JSON and executable Zod contract each have pinned SHA256 hashes
in `scripts/consume_federation_delivery.mjs`. A source update requires review
of both the producer commit and hashes; it is not a floating `main` read.

The workflow validates source checkout identity, installs the source package's
pinned Zod dependency, runs its five schema negative controls, checks consumer
replay and two payload tamper controls, and emits an immutable receipt.
Two matrix jobs each obtain a fresh checkout and emit separate receipts.
Runtime evidence carries the ABACUS workflow carrier SHA, run ID, attempt,
repeat ID. Runner names stay in local intermediate data. Both jobs must pass;
the dependent comparison job validates their receipt digests and action IDs.
On pull requests the carrier can be GitHub's merge-test SHA, not the PR head.
Local execution is explicitly LOCAL_VALIDATION, with no hosted runtime claim.

Run against an exact producer checkout:

```sh
node scripts/test_federation_delivery.mjs producer/federation/delivery/FED_PCA_20260912
node scripts/consume_federation_delivery.mjs producer/federation/delivery/FED_PCA_20260912 reports/federation_delivery/consumer_receipt.json
```

The result STRUCTURE_VALIDATED means the reviewed register was consumed and
passed its Zod contract. It does not refresh historical action states, verify
linked CI evidence, invoke child engineering acceptance, or promote DoV.
The R1 register remains a historical snapshot; new telemetry requires a new
controlled release and regenerated outputs, not silent modification of R1.

Next gate: hosted receipt, independent fresh-checkout repeat, then a reviewed
child ACCEPT/REJECT/DEFER adapter. Same-process replay alone is not the
independent repeat gate. Cryoplant runner availability remains independent.

## Approved receipt-only artifact policy (2026-09-14)

The user explicitly approved uploading hashes, IDs, counts and dispositions
to GitHub Actions artifacts in GBOGEB/ABACUS. Raw logs, source payloads,
free-text descriptions, timestamps and runner names are excluded from these
artifacts. The workflow uses exact single-file upload paths, not directories
or globs, and seven-day retention. Ordinary Actions service logs are separate
from uploaded artifacts; raw consumer output is redirected to runner-local
temporary files and is not uploaded.

`scripts/federation_receipt_policy.mjs` projects a fixed 15-field allowlist
and validates each permitted value. The repeat comparator rejects extra
fields, missing/duplicate repeats, and mismatched producer, payload, contract,
consumer carrier, workflow run or attempt bindings. Its output contains only
IDs, hashes, counts and fixed dispositions. Six policy tests include sentinel
raw fields that must never survive projection.

Only two consumer receipts and one comparison receipt are uploaded. No
governance log/report upload expansion is included. Existing unrelated
workflow artifact policies are unchanged. This workflow validates the pinned
historical R1 register; it cannot refresh R1 action statuses or confer child
engineering acceptance. REPEAT_MATCH is scoped runtime repeatability, not
global DoV. Hosted execution must still be observed at the actual CI SHA.
