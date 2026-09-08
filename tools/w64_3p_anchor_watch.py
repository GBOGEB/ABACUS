#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def metric_status(current: float, center: float, sigma: float, history_z: list[float] | None = None) -> dict[str, object]:
    if sigma <= 0:
        return {"status": "WARNING", "z_score": None, "reason": "nonpositive_sigma", "reopen_analyze": False}
    z = (current - center) / sigma
    az = abs(z)
    status = "CONTROLLED"
    if az >= 6:
        status = "DRIFT"
    elif az >= 3:
        status = "BREACH"
    elif az >= 2:
        status = "WARNING"
    hist = list(history_z or []) + [z]
    if status != "DRIFT":
        same_sign_breaches = [x for x in hist[-2:] if abs(x) >= 3 and (x > 0) == (z > 0)]
        warn_same = [x for x in hist[-5:] if abs(x) >= 2 and (x > 0) == (z > 0)]
        if len(same_sign_breaches) >= 2 or len(warn_same) >= 3:
            status = "DRIFT"
    return {"status": status, "z_score": z, "reopen_analyze": status == "DRIFT"}


def cosine_abs(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x*y for x, y in zip(a, b))
    na = math.sqrt(sum(x*x for x in a))
    nb = math.sqrt(sum(y*y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return abs(dot / (na * nb))


def pca_status(current: dict[str, object], anchor: dict[str, object], prior_statuses: list[str] | None = None) -> dict[str, object]:
    c = [float(x) for x in current.get("loadings", [])]
    a = [float(x) for x in anchor.get("loadings", [])]
    similarity = cosine_abs(c, a)
    ev_now = float(current.get("explained_variance", 0.0))
    ev_ref = float(anchor.get("explained_variance", 0.0))
    ev_delta = abs(ev_now - ev_ref)
    semantic_changed = str(current.get("semantic_label", "")) != str(anchor.get("semantic_label", ""))
    status = "CONTROLLED"
    if similarity < 0.85 or ev_delta >= 0.10 or semantic_changed:
        status = "BREACH"
    elif similarity < 0.90 or ev_delta >= 0.05:
        status = "WARNING"
    prev = list(prior_statuses or [])
    if status == "BREACH" and prev and prev[-1] == "BREACH":
        status = "DRIFT"
    return {"status": status, "cosine_similarity": similarity, "explained_variance_delta": ev_delta, "semantic_changed": semantic_changed, "reopen_analyze": status == "DRIFT"}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    out = {"schema_version": "TRIAGE-3P-ANCHOR-WATCH-1.0.0", "metrics": [], "pca": []}
    for m in payload.get("metrics", []):
        out["metrics"].append({"anchor_id": m.get("anchor_id"), **metric_status(float(m["current"]), float(m["center"]), float(m["sigma"]), [float(x) for x in m.get("history_z", [])])})
    for pc in payload.get("pca", []):
        out["pca"].append({"anchor_id": pc.get("anchor_id"), **pca_status(pc["current"], pc["anchor"], list(pc.get("prior_statuses", [])))})
    out["reopen_measure_analyze"] = any(x.get("reopen_analyze") for x in out["metrics"] + out["pca"])
    dest = Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
