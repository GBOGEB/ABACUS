#!/usr/bin/env python3
import re
import sys
import json
import shlex
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
OUT_ROOT = ROOT / "DMAIC_V3_OUTPUT" / "md_exec"

FENCE_RE = re.compile(r"```([^\n`]+)\n(.*?)```", re.DOTALL)

def run_block(lang: str, code: str) -> subprocess.CompletedProcess:
    if lang in ("bash", "sh"):
        return subprocess.run(["bash", "-lc", code], capture_output=True, text=True)
    if lang == "python":
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as tf:
            tf.write(code)
            tf.flush()
            return subprocess.run([sys.executable, tf.name], capture_output=True, text=True)
    return subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=f"Unsupported lang: {lang}")

def main():
    if len(sys.argv) < 2:
        print("Usage: markdown_exec_runner.py <markdown_file>")
        return 2

    md_path = Path(sys.argv[1]).resolve()
    if not md_path.exists():
        print(f"Not found: {md_path}")
        return 2

    text = md_path.read_text(encoding="utf-8")
    doc_name = md_path.stem
    out_dir = OUT_ROOT / doc_name / datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out_dir.mkdir(parents=True, exist_ok=True)

    summary = {
        "document": str(md_path),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "blocks": [],
        "passed": True,
    }

    idx = 0
    for m in FENCE_RE.finditer(text):
        info = m.group(1).strip()  # e.g., "python exec:assert" or "bash exec"
        code = m.group(2)
        tokens = [t.strip() for t in info.split()]
        lang = tokens[0] if tokens else ""
        if "exec" not in info:
            continue
        assert_mode = "assert" in info

        idx += 1
        res = run_block(lang, code)
        bsum = {
            "index": idx,
            "lang": lang,
            "assert": assert_mode,
            "returncode": res.returncode,
        }

        (out_dir / f"block_{idx:03d}.{lang}.out").write_text(res.stdout or "", encoding="utf-8")
        (out_dir / f"block_{idx:03d}.{lang}.err").write_text(res.stderr or "", encoding="utf-8")
        summary["blocks"].append(bsum)

        if assert_mode and res.returncode != 0:
            summary["passed"] = False
            break

    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Executed {idx} exec blocks; passed={summary['passed']}. Outputs: {out_dir}")
    return 0 if summary["passed"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
