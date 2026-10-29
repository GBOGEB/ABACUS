# MYRRHA WCS Handover — Federation Pointer & Snapshot Notice

> **Status:** This folder is a **self-contained reference snapshot** (handover **v0.4.7**) of the
> MYRRHA QPLANT Warm Compressor Station (WCS) engineering handover. It is preserved here as a
> browsable, dependency-free HTML package. It is **not** the live single source of truth.

## Where the live content now lives (GBOGEB federation)

The MYRRHA / ALaT / LKT / PVPS / WCS engineering content has since matured across the three-plane
GBOGEB federation. Use these as the authoritative homes:

| Plane | Repository | Role | Canonical WCS/MYRRHA content |
|-------|-----------|------|------------------------------|
| **Engineering SSOT** | [`GBOGEB/cryoplant-project`](https://github.com/GBOGEB/cryoplant-project) *(private)* | QPS engineering SSOT, OCD/ADR, release identity, owner approval | `PVPS/canonical/`, `architecture/w59/`, `controls/QPS_ALAT_*`, `controls/QPS_LKT_*` |
| **Semantic / publication** | [`GBOGEB/CODEX`](https://github.com/GBOGEB/CODEX) | KEB semantic-provenance, federation contracts, Pages publication | `rtm_integration/contract_followup/alat_clarification_bridge/`, `docs/qps-slide-system/`, `07_ops/qps_roundtrip/` |
| **Analytical runtime** | [`GBOGEB/ABACUS`](https://github.com/GBOGEB/ABACUS) *(this repo)* | DOW analytical runtime, first-red diagnosis, CI, security | `qplant/`, `analyses/compressors/`, `content/qplant/`, `integration/cryoplant_project/` |

## How to use this snapshot

- Open `index.html` in any browser — no build step, no server, no external dependencies.
- The single source of truth **for this snapshot** is `master/data.json` (rebuild views with
  `python3 master/render_all.py`).
- For any **current** engineering decision, defer to `cryoplant-project` (engineering SSOT) and the
  federation receipts in CODEX. Treat the numbers in this snapshot as historical to handover v0.4.7.

## Provenance

- Handover package version: **v0.4.7**
- Original integration: PR [#437](https://github.com/GBOGEB/ABACUS/pull/437) (merged 2026-05-20;
  content subsequently reorganised into the federation structure above).
- Source documents: ALaT pre-study (C1393, 09/02/2023) & Kaeser FSD 575 SFC datasheet; LKT
  pre-study & Kaeser FSD 475 SFC datasheet.
