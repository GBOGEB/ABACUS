# Session Lifecycle — GBOGEB/ABACUS

This document consolidates the canonical model for conversation/session
lifecycle management in the ABACUS federation runtime plane (DELTA_1).

---

## 1. Session Open Criteria

A session is considered **open** when:

| Criterion | Source |
|-----------|--------|
| `session_id` assigned (UUID v4) | `src/dmaic/tuple_metadata.py` |
| `STATUS_VALUES` entry set to `active` | `src/dmaic/tuple_metadata.py` |
| All `REQUIRED_TUPLE_FIELDS` present in handover JSON | `src/dmaic/tuple_metadata.py` |
| Iteration counter initialised (≥ 1) | caller contract |
| Federation plane reachable (`federation.assimilate()` → `"ok"`) | `src/dmaic/federation.py` |

---

## 2. Session Tuple Fields

Defined in `src/dmaic/tuple_metadata.py`:

```
REQUIRED_TUPLE_FIELDS = [
    "session_id",   "iteration",  "timestamp",
    "status",       "phase",      "artefacts",
    "acceptance"
]
```

### Extended Metadata (recommended additions)

| Field | Type | Description |
|-------|------|-------------|
| `semantic_tags` | list[str] | Concept labels for knowledge-basis indexing |
| `topographic_refs` | list[str] | File/path anchors touched in session |
| `progress_pct` | float (0-100) | Milestone completion percentage |
| `parent_session_id` | str \| null | Link to preceding session for chain traceability |
| `federation_moniker` | str | e.g. `DELTA_1` |

---

## 3. In-Flight Handover (Tuple Hand-off)

When context limits are reached mid-session:

1. Serialise current tuple to `handover/HANDOVER_MANIFEST.yaml`
2. Write session snapshot to `docs/patch.md` (single-file patch bundle format)
3. Set `status = suspended` in tuple
4. Commit with `[skip ci]` to avoid triggering full pipeline on partial state

Reference: `deepagent-handover-package/handover/` (01-06 documents),
`handover/HANDOVER_MANIFEST.yaml`.

---

## 4. Session Close Criteria

A session is **closed** when ALL of the following hold:

- [ ] All DMAIC phases in scope returned `(True, result_dict)`
- [ ] `python -m pytest DMAIC_V3/tests -q` passes (0 failures)
- [ ] `bash scripts/verify_workflows.sh` passes
- [ ] `python scripts/validate_docs_links.py` passes
- [ ] `federation.assimilate()` returns `status == "ok"`
- [ ] Tuple `status` updated to `completed`
- [ ] `docs/patch.md` updated with final artefact manifest
- [ ] PR opened and linked in `handover/HANDOVER_MANIFEST.yaml`

---

## 5. Patch Bundle Format

`docs/patch.md` is the canonical single-file session patch bundle. It must
contain a manifest header block:

```markdown
## SESSION PATCH MANIFEST
session_id: <uuid>
iteration:  <n>
timestamp:  <ISO-8601>
status:     completed | suspended
sha256:
  federation/manifest.yaml: <hash>
  src/dmaic/federation.py:  <hash>
  ...
```

Followed by inline file blocks (`## path/to/file` + fenced code).

---

## 6. Related Files

| File | Role |
|------|------|
| `src/dmaic/tuple_metadata.py` | Tuple schema + validation |
| `src/dmaic/federation.py` | Federation assimilation hook |
| `federation/manifest.yaml` | Global federation entry point |
| `handover/HANDOVER_MANIFEST.yaml` | Session acceptance criteria |
| `runtime/federation/codex-abacus-federation.yaml` | DELTA_1 spec |
| `docs/FEDERATION_TOPOLOGY.md` | Topology narrative |
| `docs/CODEX_ABACUS_FEDERATION_MATRIX.md` | Capability matrix |
| `abacus_v21_session_tuple_analyzer.py` | Legacy tuple analyser (root) |
| `DMAIC_V3/tests/test_smoke_federation.py` | Smoke tests for federation |
