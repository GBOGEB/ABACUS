#!/usr/bin/env python3
"""Validate fixture-wrapped or root W04 DOW receipts."""
from __future__ import annotations
import hashlib, json, re, sys
from pathlib import Path
from typing import Any
import yaml

CORR = "QPS-FED-W04-T10-SAFE-CTRL"
RUNTIME_REQUIRED = {"run_id","artifact_id","parent_repository","parent_commit_sha","child_source_ref","correlation_id","input_hash","output_hash","requested_analysis_scope","executed_analysis_scope","stage_status","typed_findings","child_disposition_placeholder","authority_boundary"}

def load(path: Path) -> dict[str, Any]:
 data = yaml.safe_load(path.read_text(encoding="utf-8"))
 if not isinstance(data, dict): raise ValueError("receipt must be a YAML mapping")
 return data

def validate(data: dict[str, Any]) -> list[str]:
 errors=[]; wrapped="example_valid_receipt" in data; receipt=data.get("example_valid_receipt") if wrapped else data
 if not isinstance(receipt, dict): return ["receipt missing or not a mapping"]
 if receipt.get("correlation_id") != CORR: errors.append("correlation_id mismatch")
 if "QPS_child_disposes" not in str(receipt.get("authority_boundary", "")): errors.append("child authority boundary missing")
 stages=receipt.get("stage_status")
 if not isinstance(stages, dict): errors.append("stage_status must be a mapping")
 if wrapped: return errors
 missing=sorted(RUNTIME_REQUIRED-set(receipt))
 if missing: errors.append("missing runtime fields: "+", ".join(missing))
 if not re.fullmatch(r"[0-9a-f]{40}", str(receipt.get("parent_commit_sha", ""))): errors.append("parent_commit_sha must be resolved")
 if receipt.get("requested_analysis_scope") != receipt.get("executed_analysis_scope"): errors.append("requested/executed analysis scope mismatch")
 if isinstance(stages, dict):
  required={"stage_id","mechanic_path","executed","status","reason"}
  for key,value in stages.items():
   if not isinstance(value,dict) or required-set(value): errors.append(f"stage {key} lacks typed execution status")
   elif value.get("executed") is not True: errors.append(f"stage {key} was not executed")
 payload=json.dumps({k:v for k,v in receipt.items() if k!="output_hash"},sort_keys=True,separators=(",",":")).encode()
 if hashlib.sha256(payload).hexdigest()!=receipt.get("output_hash"): errors.append("output_hash mismatch")
 return errors

def main(argv: list[str]) -> int:
 path=Path(argv[1]) if len(argv)>1 else Path("tests/fixtures/qps_w04_dow_receipt_fixture.yaml")
 errors=validate(load(path))
 for error in errors: print("ERROR: "+error,file=sys.stderr)
 if not errors: print(f"OK: {path} satisfies QPS W04 DOW receipt contract")
 return 1 if errors else 0
if __name__ == "__main__": raise SystemExit(main(sys.argv))
