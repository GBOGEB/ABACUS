#!/usr/bin/env bash
# Read-only CBD W48 pre-PR testflight. No network, GitHub API or mutations.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PYTHON="${PYTHON:-python3}"
NODE="${NODE:-node}"
"$PYTHON" -m unittest discover -s tests -p 'test_cbd_recurse_fanout_w48.py' -v
"$NODE" --test scripts/test_cbd_recurse_public_w48.mjs
OUT_DIR="$(mktemp -d)"
trap 'rm -rf "$OUT_DIR"' EXIT
"$PYTHON" scripts/cbd_recurse_fanout_w48.py \
  --input docs/ci/CBD_RECURSE_W48_SYNTHETIC.json \
  --manifest ci/cbd_recurse_local_w48.yaml \
  --output "$OUT_DIR/structural.json"
"$NODE" scripts/cbd_recurse_public_w48.mjs \
  "$OUT_DIR/structural.json" "$OUT_DIR/public.json"
"$PYTHON" - "$OUT_DIR/public.json" <<'PY'
import json
import sys
from pathlib import Path
value = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert value["governed_merge_admission"] == "HOLD"
assert value["canonical_root_open"] is None
assert value["authenticated_crew_launch"] is None
print("W48 local Python + JS + YAML + taskrunner contract PASS (synthetic)")
PY
