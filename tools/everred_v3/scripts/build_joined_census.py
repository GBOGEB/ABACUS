import json
import pathlib
import sys

P = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(P / "src"))
from everred import read_ledger
from joined_census import join

result = join(read_ledger(P / "data/ledger.jsonl"))
(P / "data/joined_native.json").write_text(
    json.dumps(result, indent=2, sort_keys=True) + "\n"
)
print("Joined run groups:", result["run_group_count"])
