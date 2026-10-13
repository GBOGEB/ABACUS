"""Read-only fingerprinted Bandit census; does not grant security clearance.

Classify touched-test B101 separately from other Bandit findings without suppressing
any finding or changing the existing fail-closed scanner threshold.
"""
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path


def classify(report: dict) -> dict:
    rows = []
    for item in report.get("results", []):
        rule = str(item.get("test_id", "UNKNOWN"))
        path = str(item.get("filename", ""))
        line = item.get("line_number")
        text = str(item.get("code", "")).strip()
        semantic = "TEST_ASSERTION" if rule == "B101" and (
            path.replace("\\", "/").split("/")[-2:-1] == ["tests"]
            or Path(path).name.startswith("test_")
        ) else "OTHER_FINDING"
        fingerprint = hashlib.sha256(
            json.dumps([rule, path.replace("\\", "/"), line, text],
                       sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        rows.append({"rule": rule, "path": path, "line": line,
                     "classification": semantic, "fingerprint": fingerprint})
    rows.sort(key=lambda x: (x["rule"], x["path"], str(x["line"]), x["fingerprint"]))
    return {"schema": "bandit-touched-census/1",
            "findings": rows,
            "counts_by_rule": dict(sorted(Counter(x["rule"] for x in rows).items())),
            "classification_counts": dict(sorted(Counter(x["classification"] for x in rows).items())),
            "security_clearance": None,
            "disposition": "PENDING_INDEPENDENT_SECURITY_REVIEW"}


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: bandit_touched_census.py bandit.json out.json")
    data = classify(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")))
    target = Path(sys.argv[2])
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"counts_by_rule": data["counts_by_rule"],
                      "classification_counts": data["classification_counts"],
                      "disposition": data["disposition"]}, sort_keys=True))
