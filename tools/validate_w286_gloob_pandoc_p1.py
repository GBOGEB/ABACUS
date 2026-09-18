#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "architecture/w286/W286_GLOOB_PANDOC_P1_RECEIVER_HOLD_v0.1.json"
D = json.loads(P.read_text(encoding="utf-8"))
assert D["repo"] == "GBOGEB/ABACUS"
assert D["authority_role"] == "DOW_DERIVED_ANALYSIS_CONSUMPTION"
assert D["producer"]["merge_sha"] == "3ce6078a12b2fd139f7a674db5d5cf99df6e90da"
assert D["producer"]["proof_head_sha"] == "446d1b4520fe991bd18482bcc21939a8c5538170"
assert D["producer"]["proof_run_id"] == 35372225076
assert D["producer"]["status"] == "PROVEN_MERGED"
assert D["authority_transfer"] is False
assert "promote_QPS_engineering_truth" in D["must_not"]
assert D["formal_credit_delta"] == 0
print("PASS W286 ABACUS independent P1 parity")
