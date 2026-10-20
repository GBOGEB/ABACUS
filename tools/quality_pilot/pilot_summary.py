#!/usr/bin/env python3
"""Quality pilot: normalise scanner reports, draw a triage sample, score it.

Subcommands
-----------
summarize REPORTS_DIR [--sample N] [--seed S]
    Reads whatever reports exist in REPORTS_DIR, writes:
      findings.json      all findings in one normalised schema
      summary.md         counts per tool and top rules (also fine for $GITHUB_STEP_SUMMARY)
      triage_sample.csv  stratified random sample with blank verdict/minutes columns

trend TELEMETRY_JSON [TELEMETRY_JSON ...] [--out FILE]
    Run-over-run findings per tool for the burn-in (stable / rising / falling).

score TRIAGED_CSV
    Reads the filled-in sample and prints precision, minutes per real finding,
    and a gate recommendation per tool.

Standard library only, so it runs anywhere CI has Python.
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

VERDICTS = {"TP", "FP", "NOISE", "WONTFIX"}
# Gate thresholds (precision = TP / triaged). Change here, not in CI.
GATE_PRECISION = 0.50
TUNE_PRECISION = 0.20


def _load_json(path: Path):
    try:
        text = path.read_text(encoding="utf-8").strip()
        return json.loads(text) if text else None
    except (OSError, json.JSONDecodeError):
        return None


def _rel(path) -> str:
    """Make absolute paths (ruff emits them) repo-relative for readable reports."""
    p = str(path or "")
    try:
        return str(Path(p).resolve().relative_to(Path.cwd().resolve())) if p.startswith("/") else p
    except ValueError:
        return p


def _f(tool, rule, file, line, message, severity=""):
    return {
        "tool": tool,
        "rule": str(rule or "?"),
        "file": _rel(file),
        "line": int(line or 0),
        "severity": str(severity or ""),
        "message": " ".join(str(message or "").split())[:240],
    }


def parse_ruff(d: Path):
    data = _load_json(d / "ruff.json") or []
    return [
        _f("ruff", x.get("code"), x.get("filename"),
           (x.get("location") or {}).get("row"), x.get("message"))
        for x in data
    ]


MYPY_RE = re.compile(r"^(?P<file>[^:\n]+):(?P<line>\d+)(?::\d+)?: (?P<sev>error|warning): "
                     r"(?P<msg>.*?)(?:\s+\[(?P<code>[\w-]+)\])?$")


def parse_mypy(d: Path):
    p = d / "mypy.txt"
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        m = MYPY_RE.match(line.strip())
        if m:
            out.append(_f("mypy", m["code"] or "misc", m["file"], m["line"],
                          m["msg"], m["sev"]))
    return out


def parse_mypy_focus(d: Path):
    """Burn-in focused scan: stricter mypy on physics paths, scored as its own tool."""
    out = []
    p = d / "mypy-focus.txt"
    if not p.exists():
        return out
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        m = MYPY_RE.match(line.strip())
        if m:
            out.append(_f("mypy-focus", m["code"] or "misc", m["file"], m["line"],
                          m["msg"], m["sev"]))
    return out


def parse_pip_audit(d: Path):
    data = _load_json(d / "pip-audit.json")
    if data is None:
        return []
    deps = data.get("dependencies", []) if isinstance(data, dict) else data
    out = []
    for dep in deps:
        for v in dep.get("vulns", []) or []:
            fix = ", ".join(v.get("fix_versions") or []) or "no fix yet"
            out.append(_f("pip-audit", v.get("id"), f"{dep.get('name')}=={dep.get('version')}",
                          0, f"fix: {fix}", "vuln"))
    return out


def parse_gitleaks(d: Path):
    data = _load_json(d / "gitleaks.json") or []
    return [
        _f("gitleaks", x.get("RuleID"), x.get("File"), x.get("StartLine"),
           f"{x.get('Description', '')} (commit {str(x.get('Commit', ''))[:8]})", "secret")
        for x in data
    ]


def parse_opengrep(d: Path):
    data = _load_json(d / "opengrep.json") or {}
    out = []
    for r in data.get("results", []):
        rule = str(r.get("check_id", "")).split(".")[-1]
        out.append(_f("opengrep", rule, r.get("path"), (r.get("start") or {}).get("line"),
                      (r.get("extra") or {}).get("message"),
                      (r.get("extra") or {}).get("severity")))
    return out


def parse_npm_audit(d: Path):
    data = _load_json(d / "npm-audit.json") or {}
    out = []
    for name, v in (data.get("vulnerabilities") or {}).items():
        out.append(_f("npm-audit", v.get("severity"), name, 0,
                      f"range {v.get('range', '?')}; fix available: {bool(v.get('fixAvailable'))}",
                      v.get("severity")))
    return out


def parse_code_scanning(d: Path):
    """Open alerts already uploaded by existing workflows (CodeQL, Semgrep, Bandit, ...).

    Lets the pilot measure precision of tools it does not run itself.
    """
    data = _load_json(d / "code-scanning.json") or []
    if isinstance(data, dict):  # error payload, e.g. missing permission
        return []
    out = []
    for a in data:
        tool = str((a.get("tool") or {}).get("name") or "code-scanning").lower().split()[0]
        rule = a.get("rule") or {}
        inst = a.get("most_recent_instance") or {}
        loc = inst.get("location") or {}
        out.append(_f(tool, rule.get("id"), loc.get("path"), loc.get("start_line"),
                      (inst.get("message") or {}).get("text") or rule.get("description"),
                      rule.get("security_severity_level") or rule.get("severity")))
    return out


PARSERS = [parse_ruff, parse_mypy, parse_mypy_focus, parse_pip_audit, parse_gitleaks, parse_opengrep,
           parse_npm_audit, parse_code_scanning]
REPORT_FILES = {"gitleaks": "gitleaks.json", "ruff": "ruff.json", "mypy": "mypy.txt",
                "mypy-focus": "mypy-focus.txt",
                "opengrep": "opengrep.json", "pip-audit": "pip-audit.json",
                "npm-audit": "npm-audit.json"}


def collect(reports: Path):
    findings = []
    for parse in PARSERS:
        findings.extend(parse(reports))
    for i, f in enumerate(findings, 1):
        f["id"] = f"F{i:05d}"
    return findings


def stratified_sample(findings, n, seed):
    """Spread the sample across tools so a noisy tool cannot drown the others."""
    rng = random.Random(seed)
    by_tool = defaultdict(list)
    for f in findings:
        by_tool[f["tool"]].append(f)
    total = len(findings)
    if total <= n:
        return list(findings)
    picked = []
    # at least 2 per tool (if available), then proportional
    quota = {t: min(len(v), 2) for t, v in by_tool.items()}
    remaining = n - sum(quota.values())
    for t, v in by_tool.items():
        extra = round(remaining * len(v) / total)
        quota[t] = min(len(v), quota[t] + max(0, extra))
    for t, v in by_tool.items():
        picked.extend(rng.sample(v, quota[t]))
    rng.shuffle(picked)
    return picked[: max(n, len(by_tool) * 2)]


def read_timings(reports: Path):
    """timings.csv lines: tool,seconds,exit_code,version (written by the workflow)."""
    p = reports / "timings.csv"
    rows = {}
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            parts = [x.strip() for x in line.split(",", 3)]
            if len(parts) >= 3 and parts[1].isdigit():
                rows[parts[0]] = {"seconds": int(parts[1]),
                                  "exit_code": int(parts[2]) if parts[2].lstrip("-").isdigit() else None,
                                  "version": parts[3] if len(parts) > 3 else ""}
    return rows


def write_telemetry(reports: Path, findings, run_id, phase):
    per_tool = Counter(f["tool"] for f in findings)
    per_rule = defaultdict(Counter)
    for f in findings:
        per_rule[f["tool"]][f["rule"]] += 1
    tel = {
        "schema": "gbogeb-quality-pilot-telemetry/1.0.0",
        "run": run_id,
        "phase": phase,
        "total": len(findings),
        "tools": {t: {"findings": per_tool.get(t, 0),
                      "top_rules": dict(per_rule[t].most_common(10))}
                  for t in sorted(set(per_tool) | set(read_timings(reports)))},
    }
    for t, timing in read_timings(reports).items():
        tel["tools"].setdefault(t, {"findings": 0, "top_rules": {}}).update(timing)
    (reports / "telemetry.json").write_text(json.dumps(tel, indent=1), encoding="utf-8")
    return tel


def trend(args):
    """Run-over-run table from telemetry.json files (current + previous runs)."""
    runs = []
    for p in args.files:
        tel = _load_json(Path(p))
        if isinstance(tel, dict) and "tools" in tel:
            runs.append(tel)
    if not runs:
        print("No telemetry files found.")
        return 0
    runs.sort(key=lambda t: int(t["run"]) if str(t.get("run", "")).isdigit() else 0)
    runs = runs[-args.last:]
    tools = sorted({t for r in runs for t in r["tools"]})
    head = "| Tool | " + " | ".join(f"#{r['run']}" for r in runs) + " | Δ first→last | Status |"
    lines = ["## Burn-in trend (findings per run)", "", head,
             "|---|" + "---:|" * len(runs) + "---:|---|"]
    for t in tools:
        vals = [r["tools"].get(t, {}).get("findings") for r in runs]
        seen = [v for v in vals if v is not None]
        delta = (seen[-1] - seen[0]) if len(seen) >= 2 else 0
        spread = (max(seen) - min(seen)) if seen else 0
        if len(seen) < 3:
            status = "warming up"
        elif spread == 0:
            status = "stable"
        elif delta > 0:
            status = "rising — investigate"
        elif delta < 0:
            status = "falling"
        else:
            status = "fluctuating — check determinism"
        cells = " | ".join("—" if v is None else str(v) for v in vals)
        lines.append(f"| {t} | {cells} | {delta:+d} | {status} |")
    secs = [sum((x.get("seconds") or 0) for x in r["tools"].values()) for r in runs]
    lines += ["", "Scan seconds per run: " + ", ".join(f"#{r['run']}={s}s" for r, s in zip(runs, secs))]
    md = "\n".join(lines) + "\n"
    if args.out:
        Path(args.out).write_text(md, encoding="utf-8")
    print(md)
    return 0


def summarize(args):
    reports = Path(args.reports)
    findings = collect(reports)
    (reports / "findings.json").write_text(json.dumps(findings, indent=1), encoding="utf-8")
    tel = write_telemetry(reports, findings, args.run, args.phase)

    per_tool = Counter(f["tool"] for f in findings)
    lines = [f"# Quality pilot — run {args.run} ({args.phase})", "",
             f"**Total findings:** {len(findings)}", "",
             "| Tool | Findings | Top rules |", "|---|---:|---|"]
    ran_here = [t for t, fn in REPORT_FILES.items() if (reports / fn).exists()]
    existing = sorted(t for t in per_tool if t not in REPORT_FILES)
    for tool in ran_here + existing:
        rules = Counter(f["rule"] for f in findings if f["tool"] == tool).most_common(4)
        top = ", ".join(f"`{r}` ×{c}" for r, c in rules) or "—"
        origin = "" if tool in REPORT_FILES else " *(existing workflow)*"
        t = tel["tools"].get(tool, {})
        timing = f" · {t['seconds']}s" if "seconds" in t else ""
        lines.append(f"| {tool}{origin}{timing} | {per_tool.get(tool, 0)} | {top} |")

    # de-duplicate (file, line) so overlapping tools (mypy + mypy-focus) don't double-count
    hot = Counter(p for p, _ in {(f["file"], f["line"]) for f in findings if f["line"]}).most_common(5)
    if hot:
        lines += ["", "**Hotspot files:** " + ", ".join(f"`{p}` ({c})" for p, c in hot)]

    sample = stratified_sample(findings, args.sample, args.seed)
    with (reports / "triage_sample.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "tool", "rule", "file", "line", "message",
                    "verdict(TP/FP/NOISE/WONTFIX)", "minutes", "notes"])
        for f in sample:
            w.writerow([f["id"], f["tool"], f["rule"], f["file"], f["line"], f["message"], "", "", ""])
    lines += ["", (f"Triage sample: {len(sample)} findings in `triage_sample.csv` "
                   f"(seed {args.seed}). Fill verdict + minutes, then run `score`.")]

    md = "\n".join(lines) + "\n"
    (reports / "summary.md").write_text(md, encoding="utf-8")
    print(md)
    return 0


def score(args):
    with open(args.csv, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    vcol = next((c for c in rows[0] if c.startswith("verdict")), "verdict") if rows else "verdict"
    stats = defaultdict(lambda: Counter())
    minutes = defaultdict(float)
    skipped = 0
    for r in rows:
        v = (r.get(vcol) or "").strip().upper()
        if v not in VERDICTS:
            skipped += 1
            continue
        stats[r["tool"]][v] += 1
        try:
            minutes[r["tool"]] += float(r.get("minutes") or 0)
        except ValueError:
            pass

    print(f"{'tool':<10} {'triaged':>7} {'TP':>4} {'precision':>9} {'min/TP':>7}  decision")
    for tool, c in sorted(stats.items()):
        n = sum(c.values())
        tp = c["TP"]
        prec = tp / n if n else 0.0
        mpt = f"{minutes[tool] / tp:.1f}" if tp else "—"
        if tool in {"gitleaks", "pip-audit", "npm-audit"} and tp:
            decision = "GATE now (any real hit is high-cost)"
        elif n < 3:
            decision = "too few samples — triage more"
        elif prec >= GATE_PRECISION:
            decision = "GATE on new code (ratchet)"
        elif prec >= TUNE_PRECISION:
            decision = "keep report-only; tune rules/excludes"
        else:
            decision = "drop or rewrite rules"
        print(f"{tool:<10} {n:>7} {tp:>4} {prec:>9.0%} {mpt:>7}  {decision}")
    if skipped:
        print(f"\n{skipped} row(s) without a valid verdict were ignored.")
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("summarize")
    s.add_argument("reports")
    s.add_argument("--sample", type=int, default=20)
    s.add_argument("--seed", type=int, default=42)
    s.add_argument("--run", default="local")
    s.add_argument("--phase", default="manual", choices=["burn-in", "steady", "manual"])
    s.set_defaults(func=summarize)
    t = sub.add_parser("trend")
    t.add_argument("files", nargs="+")
    t.add_argument("--last", type=int, default=12)
    t.add_argument("--out")
    t.set_defaults(func=trend)
    c = sub.add_parser("score")
    c.add_argument("csv")
    c.set_defaults(func=score)
    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
