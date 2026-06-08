# Security Triage Report — Dependabot Alerts

**Repository**: [`GBOGEB/ABACUS`](https://github.com/GBOGEB/ABACUS)
**Report Date**: June 7, 2026
**Prepared during**: DeepAgent handover TODO completion (TODO 2.6)
**Default-branch alert count (per GitHub push notifications)**: **6 open — 3 high, 3 moderate**

---

## 1. Important Note on Data Source

> **The exact Dependabot alert records could not be retrieved programmatically.**
> The GitHub App integration in use lacks the `security_events` (Dependabot alerts read) permission — both `GET /repos/GBOGEB/ABACUS/dependabot/alerts` and `GET /repos/GBOGEB/ABACUS/vulnerability-alerts` returned **HTTP 403 — "Resource not accessible by integration"**.
>
> This report is therefore a **dependency-graph-derived triage**: it is built from the repository's **SPDX SBOM** (`GET /repos/GBOGEB/ABACUS/dependency-graph/sbom`, which *is* accessible) cross-referenced against public CVE databases (NVD, GitHub Advisory, Snyk). The alert *count* (3 high / 3 moderate) is taken from GitHub's push-time notification banner.
>
> **To obtain the authoritative alert list**, either:
> 1. Grant the [Abacus.AI GitHub App](https://github.com/apps/abacusai/installations/select_target) access to security events for this repo, **or**
> 2. View the [Security → Dependabot tab](https://github.com/GBOGEB/ABACUS/security/dependabot) directly.

---

## 2. Dependency Surface (from SBOM)

The repository declares Python dependencies across 8 `requirements*.txt` files plus one npm package and GitHub Actions. SBOM enumerated **110 package nodes**. Resolved versions of note:

| Package | Resolved Version | Source File(s) |
|---------|------------------|----------------|
| `scipy` | 1.10.1 | `qplant/requirements.txt` |
| `numpy` | 1.24.3 | `qplant/requirements.txt` |
| `pandas` | 2.0.2 | `qplant/requirements.txt` |
| `plotly` | 5.14.1 | `qplant/requirements.txt` |
| `pillow` | 11.3.0 | `MINERVA_PID/requirements.txt` |
| `cairosvg` | 2.9.0 | `MINERVA_PID/requirements.txt` |
| `python-pptx` | 1.0.2 | `MINERVA_PID/requirements.txt` |
| `openpyxl` | 3.1.5 | `MINERVA_PID/requirements.txt` |
| `pyyaml` | 6.0.2 / 6.0.3 | multiple |
| `jinja2` | unpinned (`>=3.1`) | `repo_analysis_toolkit/requirements.txt` |
| `setuptools` | transitive (unresolved) | build-time (all Python envs) |
| `typescript` | 5.9.2 | `deepagent-handover-package/.../package.json` |
| `@types/node` | 24.5.1 | same |
| `undici-types` | 7.12.0 | transitive of `@types/node` |

---

## 3. Probable Alert Mapping & Remediation

Ranked by likelihood of being the flagged alerts. Each finding states the CVE, severity, affected/fixed versions, and concrete fix.

### 🔴 HIGH — Candidate 1: `setuptools` (path traversal / RCE)
| Field | Detail |
|-------|--------|
| CVEs | **CVE-2025-47273** (CVSS 8.8, path traversal → RCE in `PackageIndex.download_url`), **CVE-2024-6345** (RCE via `package_index` download) |
| Affected | `setuptools` < **78.1.1** (47273); < **70.0.0** (6345) |
| Fixed in | **78.1.1** (and later) |
| Why flagged | `setuptools` is present as a build/transitive dependency in every Python environment in the repo; scanners commonly raise **two** separate high alerts for these CVEs. This is the most probable source of 2 of the 3 HIGH alerts. |
| **Remediation** | Add `setuptools>=78.1.1` to a constraints file or each `requirements*.txt`; upgrade CI base images / `pip install -U setuptools>=78.1.1` in workflows. |

### 🔴 / 🟠 HIGH→MODERATE — Candidate 2: `jinja2` (sandbox escape)
| Field | Detail |
|-------|--------|
| CVEs | **CVE-2025-27516** (`attr` filter sandbox breakout), **CVE-2024-56326** (CVSS 7.8, `str.format` sandbox bypass), **CVE-2024-56201** (CVSS 8.8, compiler sandbox breakout) |
| Affected | `jinja2` < **3.1.6** |
| Fixed in | **3.1.6** (3.1.5 fixes the two 2024 CVEs; 3.1.6 adds 27516) |
| Why flagged | `repo_analysis_toolkit/requirements.txt` pins `jinja2>=3.1` with **no upper/secure floor**, so resolution can land on a vulnerable version. Likely source of 1+ HIGH/MODERATE alert(s). |
| **Remediation** | Change `jinja2>=3.1` → **`jinja2>=3.1.6`** everywhere. (`DMAIC_V3/requirements.txt` already correctly pins `jinja2>=3.1.6`.) |

### 🟠 MODERATE — Candidate 3: `numpy` 1.24.3 (older release line)
| Field | Detail |
|-------|--------|
| Context | `numpy==1.24.3` (2023) in `qplant/requirements.txt`. Older NumPy lines have had advisory-flagged buffer/`.npy` deserialization issues. |
| **Remediation** | Bump to a maintained 1.26.x/2.x line consistent with other manifests (`DMAIC_V3` already uses `numpy>=2.x`). Validate `qplant` compatibility before bumping. |

### 🟠 MODERATE — Candidate 4: transitive npm `undici-types` / dev-chain
| Field | Detail |
|-------|--------|
| Context | `@types/node@24.5.1` pulls `undici-types@7.12.0` (type stubs only — no runtime code). Low real-world risk but may surface in scans. |
| **Remediation** | Keep `@types/node`/`typescript` as dev-only (already `devDependencies`); refresh on the next `npm update`. Not runtime-exploitable. |

### ✅ Assessed as NOT vulnerable (ruled out)
| Package | Finding |
|---------|---------|
| `scipy 1.10.1` | No known CVE affects 1.10.1 (Snyk: no advisories). |
| `cairosvg 2.9.0` | Latest release; all historical SSRF/DoS/XXE CVEs fixed in ≤ 2.9.0. |
| `pillow 11.3.0` | Recent; no outstanding advisory. |
| `python-pptx 1.0.2`, `openpyxl 3.1.5` | No known advisories. |

---

## 4. Recommended Remediation Plan

**Priority 1 — close the HIGH alerts (low risk, high value):**
1. Pin `setuptools>=78.1.1` (constraints file or per-requirements).
2. Pin `jinja2>=3.1.6` in `repo_analysis_toolkit/requirements.txt` (and audit any other `jinja2>=3.1`).

**Priority 2 — close MODERATE alerts:**
3. Bump `qplant` `numpy`/`pandas`/`plotly` to maintained lines after a compatibility test pass.
4. Run `npm update` in the deepagent package to refresh dev-dependency transitive tree.

**Priority 3 — process / prevention:**
5. Add a repo-root `constraints.txt` referenced by all `requirements*.txt` to enforce secure minimums centrally.
6. Enable **Dependabot security updates** (auto-PRs) in repo settings so future advisories self-remediate.
7. Grant the integration `security_events` read (or assign an owner to monitor the Security tab) so alerts are auditable programmatically.

---

## 5. Suggested `constraints.txt` (drop-in)

```text
# Security constraints — enforce minimum patched versions repo-wide.
# Reference from any requirements file with:  -c ../constraints.txt
setuptools>=78.1.1      # CVE-2025-47273, CVE-2024-6345 (HIGH, path traversal/RCE)
jinja2>=3.1.6           # CVE-2025-27516, CVE-2024-56326, CVE-2024-56201 (sandbox escape)
```

---

## 6. Status Summary

| Alert (count) | Most-probable package | Action | Owner-action required |
|---------------|----------------------|--------|----------------------|
| HIGH ×~2 | `setuptools` (CVE-2025-47273 / CVE-2024-6345) | Pin `>=78.1.1` | Apply pin + rebuild CI |
| HIGH/MOD ×~1–3 | `jinja2` (3 CVEs) | Pin `>=3.1.6` | Apply pin |
| MODERATE (remainder) | `numpy`/`plotly`/dev-chain | Version bump + `npm update` | Compatibility test then bump |

> ⚠️ **Verification caveat**: package-to-alert mapping above is inferred from the SBOM + public CVE data, **not** from the live Dependabot alert API (inaccessible — 403). Confirm against the [Security tab](https://github.com/GBOGEB/ABACUS/security/dependabot) before closing alerts.

---

*Generated as part of `deepagent-handover-package` TODO 2.6. Companion docs: `REMAINING_TODO_CHECKLIST.md`, `SESSION_HANDOVER_VERIFICATION_REPORT.md`.*
