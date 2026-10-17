# CODE PURPLE / EVERRED V3 - BD queue primary HTML I/O

Status: historical exact-source operator projection. **Not a live census, source
mutation system, authenticated root-ledger event, or merge authority.**

## Interface contract

The read-only EVERRED dashboard links to `dashboard/bd_queue.html`. Native
JSON in `data/bd_queue_20261014.json` is the input and durable evidence
reference; HTML is the primary human I/O surface. It provides:

- Root-family cards, strict priority and lane filters, keyword search
- Expandable justification, provenance leaves (PR/SHA/run/job/step/URL),
  treatment and Definition of Verification (DoV)
- Sticky high-contrast legend, card JSON export and root-ID copy
- No remote API writes, local worker dispatch, automatic root confirmation,
  merge admission, or security waiver

The snapshot has **8 groups and 16 native job observations**, from ABACUS
PR #1954 and #1955. They are MERGED in GitHub but carried red and unknown
causal/clearance evidence. Those groups contain both independent root
**candidates** and downstream rollups, never eight confirmed causal roots.

## Rebuild and verify

Run from the repository root:

```bash
python tools/everred_v3/scripts/build_bd_queue.py
python tools/everred_v3/scripts/build_bd_queue.py --check
python -m unittest discover -s tools/everred_v3/tests \
  -p test_bd_queue_dashboard.py -v
```

The normal `scripts/build_dashboard.py` invokes this generator as well, so
the historical dashboard and BD queue are synchronized. Embedded data is
safely escaped and all visible fields are inserted with `textContent`.
`--check` fails when the generated HTML has drifted. The JSON schema checks
exact known PR heads, the GitHub-native run/job links, positive IDs, no missing
rationale/DoV, and no authority promotion.

## BD classification and provenance

A native red is an **occurrence**. Repeated Black files or repeated Safety
exit codes permit a shared-signature group, not inferred causal identity.
A Root ID in the cards is an *analytical candidate ID*, not a confirmed
EVERRED `root_confirmed` ledger event or an allocated worker lease.
PR Feedback Gate cancellations and Full Red Proof Summary are **consequences**
until a different independent first-red is proven.

No downloaded or user-edited HTML/JSON export becomes authoritative. Recollect
current-main CI, reconcile SHA/config/denominators, confirm owners and verify
repairs through EVERRED's append-only ledger before changing root status.

### Evidence examples and metrics

- Both broad CI reports show 30,600 statements, 13,858 misses, 8,242
  branches and **53.58% combined** against a 75% threshold.
- #1954's changed-line coverage is separately **60/84 = 71%**. #1955's
  changed-line diff had no measurable lines. These scopes never combine.
- Both runs show Safety exit 64. Bandit reported 6,527 raw findings and zero
  parse errors, not a comparable vulnerability burndown.
- #1955 Markdown first-red is MD031 at line 12 and MD032 at line 36.
- #1954 A10 flagged two possible tender files; no confidential paths are
  copied to public cards. Authorized human review is required.

## Next acceptance

1. Attach native current-main comparable receipts, source SHA and config digest.
2. Repair formatter, DOC and source-test first-reds in bounded disjoint slices.
3. Resolve A10 and Safety only with authorized independent security review.
4. Preserve the 75% broad gate and measure changed-line coverage separately.
5. Re-run all mandated checks, document root confirmation and closure, restore
   effective branch protection, then reconsider governed admission.

Current classification: `ADMISSION_HOLD`, `security_waiver=false`,
`formal_credit_delta=0`, `engineering_credit_delta=0`.
