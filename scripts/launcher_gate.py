#!/usr/bin/env python3
"""Launcher gate: report workflow steps that launch local paths missing from the checkout.

Scope: every workflow under .github/workflows/ (top level, *.yml / *.yaml)
with a push, schedule or workflow_run trigger, i.e. workflows that run on the
default branch without a PR author watching them.

For each ``run:`` step it extracts local launch targets:

  python/python3 <script> | python -m <local.module>
  bash/sh/zsh <script>     | source/. <script>
  pwsh/powershell -File <script> or <script>.ps1
  ./path/to/executable     | cd <dir> / pushd <dir>
  pip ... -r/--requirement <file>
  uses: ./local/action

and reports targets that do not exist, unless the workflow is listed in
ledger/launcher_exceptions.yaml with an unexpired entry.

REPORT-ONLY: the exit code is always 0. Known limits are documented in
docs/ci/RED_CENSUS_README.md. Requires PyYAML.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import glob
import json
import os
import posixpath
import re
import shlex
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    print("launcher_gate: PyYAML is required (pip install PyYAML)", file=sys.stderr)
    sys.exit(0)

SCHEMA = "launcher.gate.v1"
GATED_TRIGGERS = {"push", "schedule", "workflow_run"}
EXPR = re.compile(r"\$\{\{\s*(.*?)\s*\}\}")
PY = re.compile(r"^(python(3(\.\d+)?)?|py)$")
SHELLS = {"bash", "sh", "zsh"}
PWSH = {"pwsh", "powershell", "powershell.exe", "pwsh.exe"}
SEPARATORS = {"&&", "||", ";", "|", "&", "(", ")", "{", "}", "then", "do", "else", "fi", "done", "!"}
PY_VALUE_OPTS = {"-W", "-X", "-Q"}
SCRIPT_EXT = (".py", ".sh", ".bash", ".ps1", ".psm1", ".bat", ".cmd")
WRAPPERS = {"time", "exec", "sudo", "env", "nohup", "xvfb-run"}
EXEC_PATH = re.compile(r"^\.{0,2}/?[A-Za-z0-9_.@+-]+(/[A-Za-z0-9_.@+-]+)+$")
UNKNOWN = None  # sentinel for an unresolvable working directory


def triggers_of(doc: dict) -> set[str]:
    on = doc.get("on", doc.get(True))  # PyYAML parses bare `on:` as True
    if isinstance(on, str):
        return {on}
    if isinstance(on, list):
        return {str(x) for x in on}
    if isinstance(on, dict):
        return {str(k) for k in on}
    return set()


def resolve_expressions(text: str, env: dict) -> tuple[str, bool]:
    """Substitute ${{ env.X }} (literal values) and ${{ github.workspace }}.

    Returns (text, fully_resolved). Unresolvable expressions are replaced by a
    marker so tokens containing them can be skipped.
    """
    ok = True

    def sub(m: re.Match) -> str:
        nonlocal ok
        expr = m.group(1)
        if expr == "github.workspace":
            return "."
        mm = re.fullmatch(r"env\.([A-Za-z_][A-Za-z0-9_]*)", expr)
        if mm and mm.group(1) in env:
            val = str(env[mm.group(1)])
            if "${{" not in val:
                return val
        ok = False
        return "\x00EXPR\x00"

    return EXPR.sub(sub, text), ok


def literal_env(*layers) -> dict:
    env: dict = {}
    for layer in layers:
        if isinstance(layer, dict):
            for k, v in layer.items():
                if isinstance(v, (str, int, float)) and "${{" not in str(v):
                    env[str(k)] = str(v)
    return env


HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")
REDIR = re.compile(r"^\d*(>>?|<|<<-?|<<<|&>|>&)\d*$|^\d*(>>?|<)&?\d*$")
ARRAY_OPEN = re.compile(r"^\s*(declare\s+-a\s+|local\s+)?[A-Za-z_][A-Za-z0-9_]*\+?=\(\s*$")


def _balanced(text: str) -> bool:
    try:
        shlex.split(text, comments=True)
        return True
    except ValueError:
        return False


def logical_lines(script: str) -> list[str]:
    """Shell-ish logical lines: heredoc and PowerShell here-string bodies removed,
    backslash/backtick continuations joined, multi-line quoted strings joined."""
    raw = script.splitlines()
    out: list[str] = []
    buf = ""
    i = 0
    while i < len(raw):
        line = raw[i].rstrip()
        i += 1
        if not buf and ARRAY_OPEN.match(line):  # multi-line bash array literal: data
            while i < len(raw) and raw[i].strip() != ")":
                i += 1
            i += 1
            continue
        m = HEREDOC.search(line)
        if m:  # skip heredoc body (data / inline program, not a launch)
            delim = m.group(2)
            while i < len(raw) and raw[i].strip() != delim:
                i += 1
            i += 1
        elif line.endswith(("@'", '@"')):  # PowerShell here-string
            closer = line[-1] + "@"
            while i < len(raw) and not raw[i].lstrip().startswith(closer):
                i += 1
            i += 1
        if line.endswith("\\") or (line.endswith("`") and not line.endswith("``")):
            buf += line[:-1] + " "
            continue
        buf += line
        if not _balanced(buf) and i < len(raw) and len(buf) < 20000:
            buf += "\n"
            continue
        out.append(buf)
        buf = ""
    if buf:
        out.append(buf)
    return out


def split_commands(line: str, redirects: list | None = None, guarded: list | None = None) -> list[list[str]]:
    """Split a logical line into simple commands.

    ``redirects`` collects output-redirection targets (files the step creates);
    ``guarded`` collects indexes of commands followed by ``||`` (a fallback exists).
    """
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return []
    try:
        lex = shlex.shlex(stripped, posix=True, punctuation_chars=";&|()")
        lex.whitespace_split = True
        lex.commenters = "#"
        tokens = list(lex)
    except ValueError:
        return []  # unparseable (unbalanced quoting): skip rather than guess
    cmds, cur = [], []
    seps: list[str] = []
    skip_next = None
    for t in tokens:
        if skip_next is not None:
            if skip_next and redirects is not None:
                redirects.append(t)
            skip_next = None
            continue
        if t in SEPARATORS or set(t) <= set(";&|()"):
            if cur:
                cmds.append(cur)
                seps.append(t)
            cur = []
            continue
        if REDIR.match(t):
            skip_next = ">" in t  # redirection target is a data file, not a launch
            continue
        if t[:1] in "<>" or re.match(r"^\d[<>]", t):
            if ">" in t[:3] and redirects is not None:
                redirects.append(t.lstrip("0123456789<>&"))
            continue
        cur.append(t)
    if cur:
        cmds.append(cur)
        seps.append("")
    out = []
    for c, sep in zip(cmds, seps):
        # drop leading VAR=value assignments and common wrappers
        while len(c) > 1 and (re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", c[0]) or c[0] in WRAPPERS):
            c = c[1:]
        if c and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", c[0]):
            c = []
        if c:
            if sep == "||" and guarded is not None:
                guarded.append(len(out))
            out.append(c)
    return out


def is_dynamic(token: str) -> bool:
    return "\x00EXPR\x00" in token or "$" in token or "`" in token or token.startswith("~") or "%" in token


def launch_targets(cmd: list[str]) -> list[tuple[str, str]]:
    """Return [(kind, target)] for one simple command."""
    head = cmd[0]
    base = head.rsplit("/", 1)[-1]
    args = cmd[1:]
    out: list[tuple[str, str]] = []

    if PY.match(base):
        i = 0
        while i < len(args):
            a = args[i]
            if a == "-c":
                return out
            if a == "-m" and i + 1 < len(args):
                mod = args[i + 1]
                out.append(("python-module", mod))
                if mod == "pip":
                    out.extend(requirement_targets(args[i + 2:]))
                return out
            if a in PY_VALUE_OPTS:
                i += 2
                continue
            if a.startswith("-"):
                i += 1
                continue
            out.append(("python", a))
            return out
        return out

    if base in SHELLS:
        for a in args:
            if a == "-c":
                return out
            if a.startswith("-"):
                continue
            out.append((base, a))
            return out
        return out

    if base.lower() in PWSH:
        for i, a in enumerate(args):
            if a.lower() in ("-command", "-c", "-encodedcommand"):
                return out
            if a.lower() == "-file" and i + 1 < len(args):
                out.append(("pwsh", args[i + 1]))
                return out
            if a.lower().endswith(".ps1"):
                out.append(("pwsh", a))
                return out
        return out

    if head in ("cd", "pushd", "Set-Location", "Push-Location"):
        dirs = [a for a in args if not a.startswith("-")]
        if dirs:
            out.append(("cd", dirs[0]))
        return out

    if head in ("source", ".") and args:
        out.append(("source", args[0]))
        return out

    if base in ("pip", "pip3") or (base == "uv" and args[:1] == ["pip"]):
        out.extend(requirement_targets(args))
        return out

    if EXEC_PATH.match(head) and "/" in head and (
        head.startswith(("./", "../")) or head.lower().endswith(SCRIPT_EXT)
    ):
        out.append(("exec", head))  # ./script.sh, tools/run.py, scripts/x.ps1
    return out


def requirement_targets(args: list[str]) -> list[tuple[str, str]]:
    out = []
    for i, a in enumerate(args):
        if a in ("-r", "--requirement") and i + 1 < len(args):
            out.append(("requirements", args[i + 1]))
        elif a.startswith("--requirement="):
            out.append(("requirements", a.split("=", 1)[1]))
        elif a.startswith("-r") and len(a) > 2 and not a.startswith("--"):
            out.append(("requirements", a[2:]))
    return out


class Checkout:
    def __init__(self, root: Path):
        self.root = root.resolve()

    def exists(self, rel: str) -> bool:
        if any(ch in rel for ch in "*?["):
            return bool(glob.glob(str(self.root / rel)))
        return (self.root / rel).exists()

    def module_status(self, module: str) -> str | None:
        """Return 'missing' if module looks local but is absent, else None."""
        if not re.fullmatch(r"[A-Za-z_][\w.]*", module):
            return None
        parts = module.split(".")
        if not (self.root / parts[0]).is_dir():
            return None  # not a local package (stdlib / installed)
        rel = "/".join(parts)
        if (self.root / f"{rel}.py").exists() or (self.root / rel / "__init__.py").exists() or (self.root / rel / "__main__.py").exists() or (self.root / rel).is_dir():
            return None
        return "missing"


def normalize(cwd: str, target: str) -> str | None:
    if target.startswith("/"):
        return None
    p = posixpath.normpath(posixpath.join(cwd, target))
    if p.startswith(".."):
        return None
    return "" if p == "." else p


def scan_workflow(path: Path, checkout: Checkout, rel_name: str) -> dict:
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return {"workflow": rel_name, "gated": False, "error": f"yaml: {exc}", "findings": [], "skipped": []}
    if not isinstance(doc, dict):
        return {"workflow": rel_name, "gated": False, "error": "not a mapping", "findings": [], "skipped": []}
    trig = triggers_of(doc)
    gated = sorted(trig & GATED_TRIGGERS)
    result = {"workflow": rel_name, "gated": bool(gated), "triggers": gated, "findings": [], "skipped": []}
    if not gated:
        return result
    wf_env = doc.get("env") or {}
    wf_defaults = ((doc.get("defaults") or {}).get("run") or {})
    for job_id, job in sorted((doc.get("jobs") or {}).items(), key=lambda kv: str(kv[0])):
        if not isinstance(job, dict):
            continue
        job_env = literal_env(wf_env, job.get("env"))
        job_defaults = ((job.get("defaults") or {}).get("run") or {})
        default_wd = job_defaults.get("working-directory", wf_defaults.get("working-directory", "."))
        foreign_prefixes: list[str] = []  # child checkouts (path:) and created dirs
        foreign_root = False
        created: list[str] = []  # dirs made by earlier steps of this job (mkdir, venv, clone)
        for idx, step in enumerate(job.get("steps") or [], 1):
            if not isinstance(step, dict):
                continue
            label = step.get("name") or step.get("id") or f"step {idx}"
            uses = step.get("uses")
            if isinstance(uses, str):
                if uses.startswith("actions/checkout"):
                    w = step.get("with") or {}
                    if w.get("path"):
                        p, ok = resolve_expressions(str(w["path"]), job_env)
                        if ok:
                            foreign_prefixes.append(posixpath.normpath(p))
                        else:
                            foreign_root = True
                    elif w.get("repository") and "github.repository" not in str(w.get("repository")):
                        foreign_root = True  # workspace replaced by another repo
                elif uses.startswith("./"):
                    tgt = uses.rstrip("/")
                    if not foreign_root and not checkout.exists(tgt[2:]):
                        result["findings"].append(finding(job_id, label, "local-action", uses, tgt[2:]))
                elif uses.startswith("actions/download-artifact") or uses.startswith("actions/cache"):
                    p = str((step.get("with") or {}).get("path") or "")
                    for line in p.splitlines():
                        q, ok = resolve_expressions(line.strip(), job_env)
                        if ok and q and not q.startswith(("/", "~")):
                            foreign_prefixes.append(posixpath.normpath(q))
                continue
            script = step.get("run")
            if not isinstance(script, str):
                continue
            step_env = literal_env(job_env, step.get("env"))
            wd = step.get("working-directory", default_wd)
            wd, wd_ok = resolve_expressions(str(wd), step_env)
            if foreign_root:
                result["skipped"].append({"job": job_id, "step": label, "reason": "workspace replaced by foreign checkout"})
                continue
            cwd = normalize(".", wd) if wd_ok else UNKNOWN
            if cwd is None and wd_ok:
                cwd = UNKNOWN
            text, _ = resolve_expressions(script, step_env)
            cond = step.get("if")
            for line in logical_lines(text):
                redirects: list[str] = []
                guarded_idx: list[int] = []
                cmds = split_commands(line, redirects, guarded_idx)
                if cwd is not UNKNOWN:
                    for r in redirects:
                        if not is_dynamic(r):
                            n = normalize(cwd, r)
                            if n is not None:
                                created.append(n)
                for ci, cmd in enumerate(cmds):
                    extra = {}
                    if ci in guarded_idx:
                        extra["guarded"] = "||"
                    if cond is not None:
                        extra["condition"] = str(cond)
                    if cmd[0] in ("mkdir", "New-Item") and cwd is not UNKNOWN:
                        for a in cmd[1:]:
                            if not a.startswith("-") and not is_dynamic(a):
                                n = normalize(cwd, a)
                                if n is not None:
                                    created.append(n)
                    if PY.match(cmd[0].rsplit("/", 1)[-1]) and cmd[1:3] == ["-m", "venv"] or cmd[0] in ("virtualenv", "uv") and len(cmd) > 1:
                        rest = cmd[3:] if cmd[1:3] == ["-m", "venv"] else cmd[1:]
                        pos = [a for a in rest if not a.startswith("-") and a != "venv" or a == rest[-1]]
                        if cwd is not UNKNOWN and pos and not is_dynamic(pos[-1]):
                            n = normalize(cwd, pos[-1])
                            if n is not None:
                                created.append(n)
                    if cmd[0] in ("git",) and len(cmd) > 1 and cmd[1] in ("clone", "worktree"):
                        positional = [a for a in cmd[2:] if not a.startswith("-")]
                        if cwd is not UNKNOWN and len(positional) >= 2 and not is_dynamic(positional[-1]):
                            n = normalize(cwd, positional[-1])
                            if n is not None:
                                created.append(n)
                        else:
                            cwd = UNKNOWN if cmd[1] == "clone" and len(positional) < 2 else cwd
                    for kind, target in launch_targets(cmd):
                        if kind == "cd":
                            if target in ("-", "~") or is_dynamic(target) or cwd is UNKNOWN:
                                cwd = UNKNOWN
                                continue
                            n = normalize(cwd, target)
                            if n is None:
                                cwd = UNKNOWN
                                continue
                            if not under_any(n, foreign_prefixes + created) and not checkout.exists(n or "."):
                                result["findings"].append(finding(job_id, label, "cd", target, n, extra))
                                cwd = UNKNOWN  # don't cascade findings under a missing dir
                                continue
                            cwd = n
                            continue
                        if is_dynamic(target):
                            result["skipped"].append({"job": job_id, "step": label, "reason": f"dynamic {kind} target"})
                            continue
                        if cwd is UNKNOWN:
                            result["skipped"].append({"job": job_id, "step": label, "reason": f"{kind} {target} after unresolvable cd"})
                            continue
                        if kind == "python-module":
                            if target == "pip" or cwd:
                                continue  # module resolution from a subdir is sys.path-dependent
                            if checkout.module_status(target) == "missing":
                                result["findings"].append(finding(job_id, label, kind, target, target.replace(".", "/") + ".py", extra))
                            continue
                        n = normalize(cwd, target)
                        if n is None or under_any(n, foreign_prefixes + created):
                            continue
                        if not checkout.exists(n):
                            result["findings"].append(finding(job_id, label, kind, target, n, extra))
    return result


def under_any(path: str, prefixes: list[str]) -> bool:
    for p in prefixes:
        if p in ("", "."):
            continue
        if path == p or path.startswith(p.rstrip("/") + "/"):
            return True
    return False


def finding(job: str, step: str, kind: str, target: str, resolved: str, extra: dict | None = None) -> dict:
    f = {"job": str(job), "step": str(step), "kind": kind, "target": target, "resolved": resolved}
    f.update(extra or {})
    return f


def load_exceptions(path: Path, today: _dt.date) -> tuple[dict, list[dict]]:
    if not path.exists():
        return {}, []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    active, expired = {}, []
    for entry in data.get("exceptions") or []:
        wf = entry.get("workflow")
        exp = entry.get("expires")
        if isinstance(exp, str):
            exp = _dt.date.fromisoformat(exp)
        if exp is not None and exp < today:
            expired.append(entry)
            continue
        active[wf] = entry
    return active, expired


def run_gate(root: Path, exceptions_file: Path, today: _dt.date) -> dict:
    checkout = Checkout(root)
    wf_dir = root / ".github" / "workflows"
    exceptions, expired = load_exceptions(exceptions_file, today)
    results = []
    for p in sorted(list(wf_dir.glob("*.yml")) + list(wf_dir.glob("*.yaml"))):
        rel = p.relative_to(root).as_posix()
        r = scan_workflow(p, checkout, rel)
        if rel in exceptions or p.name in exceptions:
            r["exception"] = exceptions.get(rel) or exceptions.get(p.name)
        results.append(r)
    flagged = [r for r in results if r["findings"] and "exception" not in r]
    return {
        "schema": SCHEMA,
        "mode": "report-only",
        "workflows_scanned": len(results),
        "workflows_gated": sum(1 for r in results if r["gated"]),
        "workflows_flagged": len(flagged),
        "findings_total": sum(len(r["findings"]) for r in flagged),
        "excepted": sorted(r["workflow"] for r in results if "exception" in r),
        "expired_exceptions": sorted(str(e.get("workflow")) for e in expired),
        "parse_errors": sorted(r["workflow"] for r in results if r.get("error")),
        "results": [r for r in results if r["gated"] or r.get("error")],
    }


def markdown(report: dict) -> str:
    lines = [
        "# Launcher gate (report-only)",
        "",
        f"Scanned {report['workflows_scanned']} workflows; {report['workflows_gated']} have push/schedule/workflow_run triggers; "
        f"**{report['workflows_flagged']} launch missing local paths** ({report['findings_total']} findings).",
        "",
    ]
    if report["workflows_flagged"]:
        lines += ["| Workflow | Job / step | Kind | Missing path | Note |", "|---|---|---|---|---|"]
        for r in report["results"]:
            if "exception" in r:
                continue
            for f in r["findings"]:
                note = []
                if f.get("guarded"):
                    note.append("has `||` fallback")
                if f.get("condition"):
                    note.append("step `if:`")
                lines.append(f"| `{r['workflow'].rsplit('/', 1)[-1]}` | {f['job']} / {f['step']} | {f['kind']} | `{f['resolved']}` | {', '.join(note) or '-'} |")
        lines.append("")
    if report["excepted"]:
        lines.append("Excepted via ledger/launcher_exceptions.yaml: " + ", ".join(f"`{x}`" for x in report["excepted"]))
        lines.append("")
    if report["expired_exceptions"]:
        lines.append("Expired exceptions (no longer applied): " + ", ".join(f"`{x}`" for x in report["expired_exceptions"]))
        lines.append("")
    if report["parse_errors"]:
        lines.append("YAML parse errors: " + ", ".join(f"`{x}`" for x in report["parse_errors"]))
        lines.append("")
    lines.append("Options per finding: bridge (re-point to live code), prune (remove dead steps, keep live ones), "
                 "or spec (keep as a target for code still to be written; dispatch-only only with owner approval).")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--root", type=Path, default=Path("."))
    ap.add_argument("--exceptions", type=Path, default=None)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--summary", type=Path, help="markdown summary, appended (e.g. $GITHUB_STEP_SUMMARY)")
    ap.add_argument("--today", type=_dt.date.fromisoformat, default=None, help="date for exception expiry (default: today)")
    args = ap.parse_args(argv)
    exc = args.exceptions or (args.root / "ledger" / "launcher_exceptions.yaml")
    report = run_gate(args.root, exc, args.today or _dt.date.today())
    payload = json.dumps(report, sort_keys=True, indent=1) + "\n"
    if args.out:
        args.out.write_text(payload, encoding="utf-8")
    md = markdown(report)
    print(md)
    if args.summary:
        with args.summary.open("a", encoding="utf-8") as fh:
            fh.write(md)
    return 0  # report-only, always


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 - report-only: never fail the job
        print(f"launcher_gate: internal error (report-only, exit 0): {exc}", file=sys.stderr)
        sys.exit(0)
