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
repeat ID and runner name. Both jobs must pass; compare their receipt digests
and consumed action IDs before accepting the independent repeat gate.
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
