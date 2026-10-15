"""Cold-build a user-facing, non-admitting artifact navigator from ABACUS SSOT.

Only local files are hashed. A generated binary remains pending until an
independent QPS build provides actual bytes, QA and provenance receipts.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import quote

SHA = re.compile(r"[0-9a-f]{40}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
FORMATS = {"json", "yaml", "yml", "md", "html", "xlsx", "docx", "pptx",
           "pdf", "otter"}
ROLES = {"repository_source", "generated_output", "controlled_input"}
REPO = "GBOGEB/ABACUS"
SCHEMA = "mcw.artifact.catalog.v1"
REPORT_SCHEMA = "mcw.artifact.coldbuild.v1"
BINARY = {"xlsx", "docx", "pptx", "pdf"}
DAG = ("CENSUS", "SSOT_PIN", "SOURCE_FREEZE", "NORMALIZE", "MODEL",
       "DERIVE", "RENDER", "TYPE_QA", "HASH_REPLAY", "RELEASE_REVIEW")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def relative(root, value):
    require(isinstance(value, str) and value and "\\" not in value,
            "invalid relative path")
    path = Path(value)
    require(not path.is_absolute() and not any(p in ("..", ".") for p in path.parts)
            and not value.startswith("~"), "unsafe path")
    candidate = (root / path).resolve()
    require(candidate.is_relative_to(root), "path escapes checkout")
    return candidate


def git_head(root):
    result = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                            capture_output=True, text=True, check=True)
    return result.stdout.strip()


def classify(root, node):
    fmt, role = node["format"], node["role"]
    path = node.get("path")
    if role == "repository_source":
        target = relative(root, path)
        require(target.is_file(), "source absent: " + path)
        raw = target.read_bytes()
        require(raw, "empty source: " + path)
        return {"state": "LOCAL_BYTES_VERIFIED", "sha256": digest(raw),
                "bytes": len(raw), "source_path": path,
                "preview": raw[:420].decode("utf-8", "replace")}
    if role == "controlled_input":
        if path is None:
            return {"state": "CONTROLLED_EXTERNAL_UNKNOWN", "sha256": None,
                    "bytes": None, "source_path": None}
        target = relative(root, path)
        if target.is_file():
            raw = target.read_bytes()
            require(raw, "controlled input empty")
            pinned = node.get("expected_sha256")
            require(pinned is not None and SHA256.fullmatch(pinned),
                    "controlled input needs pinned SHA-256")
            require(digest(raw) == pinned, "immutable input hash changed")
            return {"state": "INPUT_HASH_VERIFIED_UNCHANGED", "sha256": pinned,
                    "bytes": len(raw), "source_path": path}
        return {"state": "CONTROLLED_INPUT_NOT_MOUNTED", "sha256": None,
                "bytes": None, "source_path": path}
    require(role == "generated_output", "unsupported role")
    require(fmt in BINARY or fmt == "html", "generated format unsupported")
    require(node.get("generator"), "generated output missing producer")
    target = relative(root, node["generator"])
    require(target.is_file(), "generator absent: " + node["generator"])
    return {"state": "NOT_GENERATED_IN_COLD_VIEW", "sha256": None,
            "bytes": None, "source_path": node["generator"]}


def evaluate(root, catalog, style, sha):
    root = Path(root).resolve()
    require(catalog.get("schema") == SCHEMA, "catalog schema mismatch")
    require(isinstance(sha, str) and SHA.fullmatch(sha), "invalid exact commit")
    require(style.get("palette", {}).get("tokens", {}).get("define"),
            "missing canonical palette")
    require(isinstance(catalog.get("artifacts"), list), "artifacts must be array")
    ids, entries = set(), []
    for node in catalog["artifacts"]:
        require(isinstance(node, dict), "invalid artifact")
        ident = node.get("id")
        require(isinstance(ident, str) and re.fullmatch(r"[A-Za-z0-9_-]{2,80}", ident)
                and ident not in ids, "duplicate/invalid artifact ID")
        ids.add(ident)
        require(node.get("format") in FORMATS and node.get("role") in ROLES,
                "invalid artifact format or role")
        require(isinstance(node.get("title"), str) and bool(node["title"]),
                "artifact title required")
        entries.append({**node, "evidence": classify(root, node)})
    for node in entries:
        links = node.get("depends_on", [])
        require(isinstance(links, list) and len(links) == len(set(links))
                and all(link in ids and link != node["id"] for link in links),
                "invalid artifact dependency")
    visiting, visited = set(), set()
    index = {node["id"]: node for node in entries}
    def walk(ident):
        require(ident not in visiting, "cyclic artifact dependencies")
        if ident in visited:
            return
        visiting.add(ident)
        for dep in index[ident].get("depends_on", []):
            walk(dep)
        visiting.remove(ident)
        visited.add(ident)
    for ident in ids:
        walk(ident)
    require(catalog.get("triggers") and isinstance(catalog["triggers"], list),
            "missing trigger contract")
    for trigger in catalog["triggers"]:
        require(trigger.get("stage") in DAG and isinstance(trigger.get("event"), str)
                and bool(trigger["event"]), "invalid trigger")
    role_counts = {role: sum(x["role"] == role for x in entries) for role in ROLES}
    states = {s: sum(x["evidence"]["state"] == s for x in entries)
              for s in sorted(set(x["evidence"]["state"] for x in entries))}
    return {"schema": REPORT_SCHEMA, "repository": REPO, "source_sha": sha,
            "catalog_schema": SCHEMA, "style_version": style.get("version"),
            "style_sha256": digest(json.dumps(style, sort_keys=True,
                               separators=(",", ":")).encode()),
            "artifacts": entries, "role_counts": role_counts, "states": states,
            "triggers": catalog["triggers"], "stages": list(DAG),
            "binary_release_admitted": False, "authority_transfer": False,
            "merge_admission": "HOLD", "evidence_grade": "LOCAL_COLD_CHECK_ONLY",
            "semantic_delta_zero_proves_byte_identity": False,
            "note": "External binaries and generated outputs remain unverified."}


def render(report, style):
    esc = lambda x: html.escape(str(x), quote=True)
    color = style["palette"]["tokens"]
    cards = []
    for item in report["artifacts"]:
        evidence = item["evidence"]
        state = evidence["state"]
        is_verified = state in ("LOCAL_BYTES_VERIFIED", "INPUT_HASH_VERIFIED_UNCHANGED")
        state_class = "ok" if is_verified else "pending"
        local = item.get("path") if item["role"] == "repository_source" else item.get("generator")
        ref = "https://github.com/" + REPO + "/blob/" + report["source_sha"] + "/" + quote(local, safe="/") if local else ""
        link = ('<a href="' + esc(ref) + '" target="_blank" rel="noopener noreferrer">Open source ↗</a>') if ref else "<span>Controlled input — no public link</span>"
        hashtext = evidence["sha256"] or "UNKNOWN — no output bytes"
        preview = evidence.get("preview")
        leaf = ('<details class="leaf"><summary>Inspect source excerpt</summary>'
                '<pre>' + esc(preview) + '</pre></details>') if preview else ""
        cards.append(
            '<article class="artifact" data-search="' + esc((" ".join([item["title"], item["format"], item["role"], state])).lower()) +
            '" data-type="' + esc(item["format"]) + '" id="' + esc(item["id"]) + '">'
            '<div class="card-top"><span class="type">' + esc(item["format"].upper()) +
            '</span><span class="state ' + state_class + '">' + esc(state.replace("_", " ")) +
            '</span></div><h3>' + esc(item["title"]) + '</h3><p>' + esc(item.get("description", "")) +
            '</p><div class="facts"><span>Role</span><strong>' + esc(item["role"].replace("_", " ")) +
            '</strong><span>SHA-256</span><code title="' + esc(hashtext) + '">' + esc(hashtext) +
            '</code><span>Inputs</span><strong>' + esc(", ".join(item.get("depends_on", [])) or "No declared upstream") +
            '</strong></div>' + leaf + '<div class="card-foot">' + link +
            '<a href="#process">View build sequence ↓</a></div></article>'
        )
    stages = "".join('<li><span class="step-index">' + str(i + 1) + '</span><span>' +
                     esc(stage.replace("_", " ")) + '</span></li>'
                     for i, stage in enumerate(report["stages"]))
    triggers = "".join('<tr><td>' + esc(item["event"]) + '</td><td>' +
                       esc(item["stage"]) + '</td><td>' +
                       esc(item.get("action", "")) + '</td></tr>'
                       for item in report["triggers"])
    warning = ("This is a cold-build snapshot. Generated binaries and remote "
               "attestation are NOT proven.")
    missing = report.get("missing_style_probes")
    if missing:
        warning += " Missing style probes: " + ", ".join(missing) + "."
    # HTML is self contained: no network reads, no unsafe interpolation into JavaScript.
    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Mission Control Wide · Artifact Evidence</title>
<style>
:root{--purple:%s;--measure:%s;--analyze:%s;--improve:%s;--control:%s;--red:%s;--bg:#f7f7fa;--panel:#fff;--ink:#242331;--muted:#595668;--border:#dad8e2}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 Aptos,Arial,sans-serif}
[hidden]{display:none!important}a{color:var(--purple)}.shell{max-width:1200px;margin:auto;padding:0 22px 70px}
header{background:#261a35;color:white;padding:22px max(22px,calc((100vw - 1156px)/2));border-bottom:5px solid var(--purple)}
header small{letter-spacing:.1em;text-transform:uppercase;color:#d6cae1}header h1{font-size:clamp(1.6rem,3vw,2.5rem);margin:.3rem 0}
header p{max-width:800px;color:#e3dced;margin:0}.top{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px}
.anchor{background:#fff;color:var(--purple);padding:7px 13px;border-radius:8px;text-decoration:none;font-weight:700}
.notice{margin:22px 0;padding:13px 17px;border-left:4px solid var(--improve);background:#fff2e7;border-radius:6px}
.summary{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:20px 0}
.kpi{background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:15px}
.kpi b{font-size:1.8rem;display:block;color:var(--purple)}.kpi small{color:var(--muted)}
.section-title{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}
input,select{border:1px solid #958ca3;padding:10px 12px;border-radius:8px;background:#fff;font:inherit;max-width:100%%}
.controls{display:flex;gap:10px;flex-wrap:wrap;margin:14px 0 20px}
.artifacts{display:grid;grid-template-columns:repeat(auto-fill,minmax(275px,1fr));gap:14px}
.artifact{background:var(--panel);border:1px solid var(--border);border-radius:13px;padding:18px;display:flex;flex-direction:column;gap:10px}
.card-top,.card-foot{display:flex;justify-content:space-between;flex-wrap:wrap;gap:7px;align-items:center}
.type,.state{padding:4px 8px;font-size:11px;font-weight:750;border-radius:5px;letter-spacing:.02em}
.type{background:#eee5f5;color:var(--purple)}.state{background:#fef1e6;color:#85450c}.state.ok{background:#e1f4ec;color:#145940}
.artifact h3{font-size:1.09rem;margin:0}.artifact p{color:var(--muted);margin:0;flex:1}
.facts{display:grid;grid-template-columns:62px minmax(0,1fr);gap:5px;font-size:12px;border-top:1px solid var(--border);padding-top:9px}
.facts span{color:var(--muted)}.facts code{overflow-wrap:anywhere;font-size:11px}.leaf summary{cursor:pointer;font-weight:700;font-size:12px;color:var(--purple)}.leaf pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:160px;overflow:auto;font:11px/1.45 Consolas,monospace;border:1px solid var(--border);padding:8px;border-radius:7px}
.card-foot{border-top:1px solid var(--border);padding-top:12px;font-size:12px}
section{margin:32px 0}h2{font-size:1.35rem;margin:0 0 12px}
.spine{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(5,1fr);gap:9px}
.spine li{background:white;border:1px solid var(--border);border-top:3px solid var(--purple);border-radius:8px;padding:10px;min-height:72px;font-weight:650;font-size:13px}
.step-index{display:block;font-size:11px;color:var(--muted)}
.tablewrap{overflow-x:auto;background:white;border:1px solid var(--border);border-radius:10px}
table{border-collapse:collapse;width:100%%}th,td{padding:11px 13px;text-align:left;border-bottom:1px solid var(--border)}
th{background:#eee8f3;font-size:12px}td{font-size:13px}
.mono{font-family:Consolas,monospace;overflow-wrap:anywhere}
footer{color:var(--muted);font-size:12px;margin-top:35px}
@media(max-width:750px){.summary{grid-template-columns:repeat(2,1fr)}.spine{grid-template-columns:repeat(2,1fr)}}
@media(prefers-color-scheme:dark){:root{--bg:#151420;--panel:#211f2d;--ink:#f2f0f6;--muted:#c7c0d1;--border:#4d4358}
.notice{background:#32251f;color:#f2e4cd}.spine li,.tablewrap{background:var(--panel)}
th{background:#3d304b}.state{background:#53351f;color:#ffd9a5}.state.ok{background:#163c30;color:#bcefd2}
.type{background:#40304f;color:#f0d9ff}input,select{background:var(--panel);color:var(--ink)}}
</style></head><body>
<header><div class="top"><div><small>ABACUS · QPS · Evidence spine</small>
<h1>Artifact Evidence Navigator</h1><p>Find the artifact, see its origin, follow its build path. Machine formats remain available as underlying evidence.</p>
</div><a class="anchor" href="#process">Build DAG ↓</a></div></header>
<main class="shell">
<div class="notice" role="status"><strong>Qualification:</strong> %s <strong>Merge admission: HOLD.</strong></div>
<div class="summary">
<div class="kpi"><b>%d</b><small>Catalogued artifacts</small></div>
<div class="kpi"><b>%d</b><small>Actual local source files</small></div>
<div class="kpi"><b>%d</b><small>Generated output contracts</small></div>
<div class="kpi"><b>%d</b><small>Controlled inputs (unmounted unless verified)</small></div>
</div>
<section id="explore"><div class="section-title"><h2>Browse outputs and evidence</h2><span id="shown"></span></div>
<div class="controls"><input aria-label="Search artifacts" id="query" placeholder="Search format, role or title">
<select aria-label="Filter format" id="format"><option value="all">All formats</option>%s</select></div>
<div class="artifacts" id="artifacts">%s</div></section>
<section id="process"><h2>Cold build → qualified release</h2><ol class="spine">%s</ol>
<p>Normalizing or opening an Excel DataFrame with zero changed rows (<code>df Δ = 0</code>) does not establish byte identity. Compare SHA-256 for unchanged input bytes; qualify generated binaries independently.</p></section>
<section><h2>Event and stage triggers</h2><div class="tablewrap"><table><thead><tr><th>Trigger</th><th>Stage</th><th>Admissible action</th></tr></thead><tbody>%s</tbody></table></div></section>
<section><h2>Provenance and limitations</h2><div class="tablewrap"><table><tbody>
<tr><th>Repository</th><td>%s</td></tr><tr><th>Git source</th><td class="mono">%s</td></tr>
<tr><th>Style version</th><td>%s</td></tr><tr><th>Canonical style semantic SHA-256</th><td class="mono">%s</td></tr><tr><th>Style file SHA-256</th><td class="mono">%s</td></tr><tr><th>Catalog file SHA-256</th><td class="mono">%s</td></tr>
<tr><th>Evidence</th><td>%s</td></tr><tr><th>Release authority</th><td>None — native CI, independent QA and release approval required.</td></tr>
</tbody></table></div></section>
<footer>Rendered from a typed catalog and SSOT style. No external scripts, fonts or live API required. Static source visibility is not authentication.</footer>
</main><script>
const filter=()=>{const q=document.getElementById("query").value.toLowerCase(),f=document.getElementById("format").value;
let n=0;document.querySelectorAll(".artifact").forEach(el=>{const ok=el.dataset.search.includes(q)&&(f==="all"||el.dataset.type===f);
el.hidden=!ok;if(ok)n++});document.getElementById("shown").textContent=n+" visible"};
document.getElementById("query").addEventListener("input",filter);
document.getElementById("format").addEventListener("change",filter);filter();
</script></body></html>
""" % (
       color["define"], color["measure"], color["analyze"], color["improve"],
       color["control"], color["critical"], esc(warning),
       len(report["artifacts"]), report["states"].get("LOCAL_BYTES_VERIFIED", 0),
       report["role_counts"]["generated_output"], report["role_counts"]["controlled_input"],
       "".join('<option value="' + esc(fmt) + '">' + esc(fmt.upper()) + "</option>"
               for fmt in sorted({x["format"] for x in report["artifacts"]})),
       "".join(cards), stages, triggers, esc(report["repository"]), esc(report["source_sha"]),
       esc(report["style_version"]), esc(report["style_sha256"]),
       esc(report.get("style_file_sha256") or "UNKNOWN"),
       esc(report.get("catalog_file_sha256") or "UNKNOWN"), esc(report["evidence_grade"])
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, default=Path("."))
    p.add_argument("--catalog", type=Path, required=True)
    p.add_argument("--style", type=Path, required=True)
    p.add_argument("--style-status", type=Path)
    p.add_argument("--sha", help="Exact Git SHA, defaults to HEAD")
    p.add_argument("--html", type=Path, required=True)
    p.add_argument("--receipt", type=Path, required=True)
    a = p.parse_args()
    root = a.root.resolve()
    report = evaluate(root, json.loads(a.catalog.read_text()),
                      json.loads(a.style.read_text()), a.sha or git_head(root))
    report["style_file_sha256"] = digest(a.style.read_bytes())
    report["catalog_file_sha256"] = digest(a.catalog.read_bytes())
    if a.style_status:
        status = json.loads(a.style_status.read_text())
        require(status.get("valid") is True, "invalid style contract receipt")
        probes = status.get("awake", {}).get("probes", [])
        require(isinstance(probes, list), "missing style probes array")
        report["missing_style_probes"] = sorted(
            p["id"] for p in probes if p.get("awake") is False
        )
        report["style_awake_score"] = status.get("awake", {}).get("awake_score")
    content = render(report, json.loads(a.style.read_text()))
    a.html.parent.mkdir(parents=True, exist_ok=True)
    a.receipt.parent.mkdir(parents=True, exist_ok=True)
    a.html.write_text(content, encoding="utf-8")
    report["html_sha256"] = digest(content.encode())
    a.receipt.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"artifacts": len(report["artifacts"]), "html_sha256":
                      report["html_sha256"], "merge_admission": "HOLD"}))


if __name__ == "__main__":
    main()
