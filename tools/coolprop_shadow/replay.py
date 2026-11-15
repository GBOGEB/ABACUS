#!/usr/bin/env python3
"""Replay recorded CoolProp PropsSI calls under the installed CoolProp and classify.

    python tools/coolprop_shadow/replay.py --records DIR --out report.json \
        --summary summary.md [--require-identical]

Records come from tools/coolprop_shadow/hook/sitecustomize.py running the test
suite under the governed oracle (CoolProp==7.2.0). Every distinct call is
re-issued with the same argument values *and types*, and the outcome compared:

    IDENTICAL       bit-identical value (or identical error)
    ROUNDING        |rel| <= 1e-12
    DRIFT           1e-12 < |rel| <= 1e-6
    SIGNIFICANT     |rel| > 1e-6
    NEW_ERROR       recorded a value, replay raises
    FIXED_ERROR     recorded an error, replay returns a value
    ERROR_REWORDED  both raise the same exception type, message differs
    ERROR_RETYPED   both raise, exception type differs
    SHAPE_CHANGED   scalar/array or shape differs
    UNSTABLE        the same call gave different outcomes while recording
    UNREPLAYABLE    an argument type the codec cannot rebuild

Helium calls are tagged with a temperature band so drift can be read against
the QPLANT helium policy (HEPAK governs T <= 4.5 K, including He-II below the
lambda point; CoolProp governs above 4.5 K).

--require-identical (the 7.2.0 control replay) exits 1 unless every replayable
call is IDENTICAL, proving the harness itself adds no noise. Without it the
tool is report-only and exits 0; exit 2 means the harness could not run.
"""

from __future__ import annotations

import argparse
import json
import math
import platform
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "hook"))
import coolprop_shadow_codec as codec  # noqa: E402

LAMBDA_K = 2.1768
HEPAK_MAX_K = 4.5
ROUNDING = 1e-12
DRIFT = 1e-6
ORDER = [
    "SIGNIFICANT",
    "NEW_ERROR",
    "ERROR_RETYPED",
    "SHAPE_CHANGED",
    "DRIFT",
    "FIXED_ERROR",
    "ERROR_REWORDED",
    "ROUNDING",
    "UNSTABLE",
    "UNREPLAYABLE",
    "IDENTICAL",
]


def load_records(directory: Path) -> tuple[dict, list[dict]]:
    calls: dict[str, dict] = {}
    headers: list[dict] = []
    counts: Counter = Counter()
    unstable: set[str] = set()
    for path in sorted(directory.glob("calls-*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            if "header" in rec:
                headers.append(rec["header"])
            elif "key" in rec:
                entry = calls.setdefault(
                    rec["id"],
                    {
                        "key": rec["key"],
                        "outcome": rec["outcome"],
                        "sites": set(),
                        "count": 0,
                    },
                )
                if entry["outcome"] != rec["outcome"]:
                    unstable.add(rec["id"])
                entry["sites"].add(rec.get("site", "?"))
                entry["count"] += 1
            elif "counts" in rec:
                for cid, n in rec["counts"].items():
                    counts[cid] += n - 1  # first sighting already counted
            elif "unstable" in rec:
                unstable.add(rec["unstable"])
    for cid, extra in counts.items():
        if cid in calls:
            calls[cid]["count"] += extra
    for cid in unstable:
        if cid in calls:
            calls[cid]["unstable"] = True
    return calls, headers


def band(args: tuple) -> str:
    if len(args) < 6 or not isinstance(args[5], str):
        return "constant"
    if "helium" not in args[5].lower():
        return "non-helium"
    temperature = None
    for name_idx in (1, 3):
        if args[name_idx] == "T":
            try:
                temperature = float(args[name_idx + 1])
            except (TypeError, ValueError):
                return "T-array"
    if temperature is None:
        return "no-T input"
    if temperature < LAMBDA_K:
        return f"below lambda (<{LAMBDA_K} K)"
    if temperature <= HEPAK_MAX_K:
        return f"{LAMBDA_K}-{HEPAK_MAX_K} K (HEPAK governs)"
    return f">{HEPAK_MAX_K} K (CoolProp governs)"


def rel(a: float, b: float) -> float:
    if a == b:
        return 0.0
    if math.isnan(a) or math.isnan(b):
        return math.inf
    scale = max(abs(a), abs(b))
    return abs(a - b) / scale if scale > 0 else abs(a - b)


def flatten(encoded: list) -> list | None:
    """Return a list of floats for scalar or array values, None if not numeric."""
    kind = encoded[0]
    if kind == "float":
        return [float.fromhex(encoded[1])]
    if kind == "npfloat":
        return [float.fromhex(encoded[2])]
    if kind in ("int", "npint"):
        return [float(encoded[-1])]
    if kind == "ndarray":
        values = []
        for item in encoded[3]:
            sub = flatten(item)
            if sub is None:
                return None
            values.extend(sub)
        return values
    return None


def compare(old: list, new: list) -> tuple[str, float | None, str]:
    if old[0] == "error" and new[0] == "error":
        if old[1] != new[1]:
            return "ERROR_RETYPED", None, f"{old[1]} -> {new[1]}"
        if old[2] != new[2]:
            return "ERROR_REWORDED", None, new[2][:200]
        return "IDENTICAL", 0.0, ""
    if old[0] == "error":
        return "FIXED_ERROR", None, f"was {old[1]}: {old[2][:160]}"
    if new[0] == "error":
        return "NEW_ERROR", None, f"{new[1]}: {new[2][:200]}"
    a, b = old[1], new[1]
    if a == b:
        return "IDENTICAL", 0.0, ""
    if (a[0] == "ndarray") != (b[0] == "ndarray") or (
        a[0] == "ndarray" and a[2] != b[2]
    ):
        return "SHAPE_CHANGED", None, f"{a[0]} -> {b[0]}"
    fa, fb = flatten(a), flatten(b)
    if fa is None or fb is None or len(fa) != len(fb):
        return "SHAPE_CHANGED", None, f"{a[0]} -> {b[0]}"
    worst = max(rel(x, y) for x, y in zip(fa, fb))
    if worst == 0.0:
        return "IDENTICAL", 0.0, "same value, different numeric type"
    if worst <= ROUNDING:
        return "ROUNDING", worst, ""
    if worst <= DRIFT:
        return "DRIFT", worst, ""
    return "SIGNIFICANT", worst, ""


def replay(calls: dict, propssi) -> list[dict]:
    rows = []
    for cid, entry in sorted(calls.items()):
        row = {"id": cid, "count": entry["count"], "sites": sorted(entry["sites"])[:5]}
        try:
            args, kwargs = codec.decode_call(entry["key"])
        except codec.Unreplayable as exc:
            rows.append(
                {
                    **row,
                    "class": "UNREPLAYABLE",
                    "detail": str(exc),
                    "band": "?",
                    "call": entry["key"][:200],
                }
            )
            continue
        row["call"] = "PropsSI(" + ", ".join(repr(a) for a in args) + ")"
        row["output"] = args[0] if args else "?"
        row["band"] = band(args)
        if entry.get("unstable"):
            rows.append(
                {
                    **row,
                    "class": "UNSTABLE",
                    "detail": "nondeterministic while recording",
                }
            )
            continue
        try:
            new = codec.outcome_of_result(propssi(*args, **kwargs))
        except Exception as exc:  # CoolProp raises ValueError; keep any type
            new = codec.outcome_of_error(exc)
        klass, worst, detail = compare(entry["outcome"], new)
        rows.append(
            {
                **row,
                "class": klass,
                "rel": worst,
                "detail": detail,
                "recorded": entry["outcome"],
                "replayed": new,
            }
        )
    return rows


def summarise(rows: list[dict], meta: dict) -> str:
    by_class = Counter(r["class"] for r in rows)
    lines = [
        f"### CoolProp shadow replay: {meta['replay']['coolprop']} "
        f"on Python {meta['replay']['python']}",
        "",
        f"Recorded under CoolProp {', '.join(meta['recorded_coolprop']) or '?'} "
        f"on Python {', '.join(meta['recorded_python']) or '?'}: "
        f"**{len(rows)} distinct calls**, {sum(r['count'] for r in rows)} total.",
        "",
        "| Class | Distinct calls |",
        "|---|---:|",
    ]
    lines += [f"| {k} | {by_class[k]} |" for k in ORDER if by_class.get(k)]
    bands: dict[str, Counter] = defaultdict(Counter)
    for r in rows:
        bands[r.get("band", "?")][r["class"]] += 1
    lines += [
        "",
        "| Helium band | " + " | ".join(k for k in ORDER if by_class.get(k)) + " |",
        "|---|" + "---:|" * sum(1 for k in ORDER if by_class.get(k)),
    ]
    for name in sorted(bands):
        lines.append(
            f"| {name} | "
            + " | ".join(str(bands[name][k]) for k in ORDER if by_class.get(k))
            + " |"
        )
    worst_by_output: dict[str, float] = {}
    for r in rows:
        if r.get("rel") is not None:
            worst_by_output[r["output"]] = max(
                worst_by_output.get(r["output"], 0.0), r["rel"]
            )
    if worst_by_output:
        lines += ["", "| Output | Worst relative difference |", "|---|---:|"]
        lines += [f"| `{k}` | {v:.3e} |" for k, v in sorted(worst_by_output.items())]
    notable = [r for r in rows if r["class"] not in ("IDENTICAL", "ROUNDING")]
    notable.sort(key=lambda r: (ORDER.index(r["class"]), -(r.get("rel") or 0.0)))
    if notable:
        lines += [
            "",
            "<details><summary>Calls that are not identical "
            f"({len(notable)})</summary>",
            "",
            "| Class | rel | Band | Call | Detail | Call site |",
            "|---|---:|---|---|---|---|",
        ]
        for r in notable[:200]:
            value = f"{r['rel']:.2e}" if r.get("rel") is not None else ""
            detail = r.get("detail", "").replace("|", "\\|")
            lines.append(
                f"| {r['class']} | {value} | {r.get('band', '?')} | `{r['call'][:110]}` "
                f"| {detail[:120]} | {', '.join(r['sites'][:2])} |"
            )
        lines += ["", "</details>"]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--summary", type=Path)
    parser.add_argument("--require-identical", action="store_true")
    args = parser.parse_args(argv)

    calls, headers = load_records(args.records)
    if not calls:
        print(f"no recorded calls under {args.records}", file=sys.stderr)
        return 2
    try:
        import CoolProp
        from CoolProp.CoolProp import PropsSI
    except ImportError as exc:
        print(f"CoolProp is not importable: {exc}", file=sys.stderr)
        return 2

    rows = replay(calls, PropsSI)
    meta = {
        "schema": codec.SCHEMA,
        "recorded_coolprop": sorted({h.get("coolprop", "?") for h in headers}),
        "recorded_python": sorted({h.get("python", "?") for h in headers}),
        "replay": {
            "coolprop": getattr(CoolProp, "__version__", "?"),
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "classes": dict(Counter(r["class"] for r in rows)),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps({"meta": meta, "calls": rows}, indent=1, default=str) + "\n",
        encoding="utf-8",
    )
    text = summarise(rows, meta)
    if args.summary:
        args.summary.write_text(text, encoding="utf-8")
    print(text)

    if args.require_identical:
        bad = [
            r
            for r in rows
            if r["class"] not in ("IDENTICAL", "UNREPLAYABLE", "UNSTABLE")
        ]
        if bad:
            print(
                f"control replay is not identical for {len(bad)} calls", file=sys.stderr
            )
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
