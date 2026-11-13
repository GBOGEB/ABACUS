"""E0-E2 (L1_INTAKE): inventory one configured root folder, group by TYPE (A-K) and EPIC (configured epics + OTHER),
and run a reverse-Kahn tip scan over the ZIP family. Read-only: moves, renames and writes nothing outside
the root's inventory folder under ESTATE_HOME.

    python -I -X utf8 DMAIC_V3/binary_engines/estate_inventory.py [--root-id ID] [--no-hash]
"""

from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import hashlib
import json
import os
import re
import sys
import tarfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import estate_spec as _spec  # noqa: E402
import git_readonly  # noqa: E402
from ggmath_bridge import load as _load_kernel  # noqa: E402

DEPTH, ROOTS, inv_dir, EPICS, EXT_TO_TYPE = (
    _spec.DEPTH,
    _spec.ROOTS,
    _spec.inv_dir,
    _spec.EPICS,
    _spec.EXT_TO_TYPE,
)
OG5, OTHER_EPIC, PERSONAL_TOKENS, SCHEMA = (
    _spec.OG5,
    _spec.OTHER_EPIC,
    _spec.PERSONAL_TOKENS,
    _spec.SCHEMA,
)
TYPE_LETTER, TYPES = _spec.TYPE_LETTER, _spec.TYPES

MAGIC = {  # first bytes -> family; the extension alone proves nothing (K-ANY-01)
    b"PK\x03\x04": "zip",
    b"PK\x05\x06": "zip",
    b"%PDF": "pdf",
    b"\x89PNG": "png",
    b"\xff\xd8\xff": "jpeg",
    b"GIF8": "gif",
    b"\x1f\x8b": "gzip",
    b"\xd0\xcf\x11\xe0": "ole",
    b"# v2 git bundle": "gitbundle",
}
EXPECT = {
    "DOCX": "zip",
    "XLSX": "zip",
    "PPTX": "zip",
    "VSDX": "zip",
    "ZIP": "zip",
    "PDF": "pdf",
    "PNG": None,
}
VERSION_RX = re.compile(
    r"(\(\d+\)|[ _-]?v\d+(?:[._]\d+)*|[ _-]?\d{8}(?:[-_]\d{4,6})?|[ _-]?\d{4}[-_]\d{2}[-_]\d{2}|"
    r"[ _-]?\d{4}(?=$|[ _-])|[ _-](?:final|draft|copy|corrected|updated|enhanced|new|old|full|rev\w*))",
    re.I,
)
HANDOVER_RX = re.compile(r"handover|manifest|dropin|package|deliverable|bundle", re.I)
REPO_MARKERS = (
    ".git/HEAD",
    "pyproject.toml",
    "package.json",
    ".github/",
    "setup.py",
    "requirements.txt",
)


SENSITIVE_DIRS = {
    ".ssh",
    ".aws",
    ".azure",
    ".gnupg",
    ".config",
    ".docker",
    ".kube",
    "_personal",
    "_canonical_private",
}


def _is_link(e: os.DirEntry) -> bool:
    """True for symlinks and directory junctions (reparse points on folders); file placeholders from OneDrive are not links."""
    if e.is_symlink():
        return True
    try:
        st = e.stat(follow_symlinks=False)
    except OSError:
        return True
    return bool(
        e.is_dir(follow_symlinks=False) and getattr(st, "st_file_attributes", 0) & 0x400
    )  # FILE_ATTRIBUTE_REPARSE_POINT


def estate_files(root: Path, entries: list):
    """Files the estate owns: every file at the top level, plus files inside the GG_* folders the estate itself created when
    it grouped them (so grouped files keep their identity, family and truth status). Other folders are never entered; links
    are never followed. Yields (name relative to root with '/', absolute path, stat, location).
    """
    for e in entries:
        if e.is_file(follow_symlinks=False) and not _is_link(e):
            yield e.name, Path(e.path), e.stat(follow_symlinks=False), "root"
    for e in entries:
        if (
            e.is_dir(follow_symlinks=False)
            and not _is_link(e)
            and e.name.startswith("GG_")
        ):
            for dp, dns, fns in os.walk(e.path, followlinks=False):
                dns[:] = sorted(
                    d for d in dns if not os.path.islink(os.path.join(dp, d))
                )
                for fn in sorted(fns):
                    ap = Path(dp) / fn
                    if not ap.is_symlink():
                        yield ap.relative_to(root).as_posix(), ap, ap.stat(), "grouped"


def family_stem(name: str) -> str:
    stem = Path(name).stem
    if stem.lower().endswith(".tar"):
        stem = stem[:-4]
    prev = None
    while prev != stem:
        prev, stem = stem, VERSION_RX.sub("", stem).strip(" _-.")
    return re.sub(r"[ _\-.]+", "_", stem).upper() or Path(name).stem.upper()


def tokens(name: str) -> list[str]:
    return [t.upper() for t in re.findall(r"[A-Za-z]{2,}", Path(name).stem)]


def classify_epic(name: str, extra: str = "") -> tuple[str, str | None, int, list[str]]:
    toks = tokens(name) + tokens(extra)
    if PERSONAL_TOKENS & set(toks):
        return ("E0_OTHER", "_personal", 0, sorted(PERSONAL_TOKENS & set(toks)))
    best = (OTHER_EPIC[0], OTHER_EPIC[1], 0, [])
    for epic, repo, kw in EPICS:
        hits = [t for t in toks if t in kw]
        score = sum(kw[t] for t in hits)
        if score > best[2]:
            best = (epic, repo, score, sorted(set(hits)))
    return best


def sniff(path: Path) -> str:
    try:
        with path.open("rb") as fh:
            head = fh.read(16)
    except OSError:
        return "unreadable"
    for sig, fam in MAGIC.items():
        if head.startswith(sig):
            return fam
    return (
        "text"
        if head and all(32 <= b < 127 or b in (9, 10, 13) for b in head[:12])
        else "other"
    )


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def staleness(age_days: float) -> str:
    return (
        "HOT"
        if age_days < 30
        else "WARM" if age_days < 120 else "COLD" if age_days < 365 else "FROZEN"
    )


def git_tracked(root: Path) -> set[str] | None:
    """Tracked names at the top level and in the estate's GG_ folders, read from the index (git is never run).
    None: the root is in a repository whose index cannot be read, so every file counts as tracked (fail closed).
    """
    paths = git_readonly.tracked_paths(root)
    if paths is None:
        return None
    return {
        p for p in paths if p and ("/" not in p or p.startswith("GG_"))
    }  # top level + estate GG_ folders


# ------------------------------------------------------------------ ZIP deep read (up to 5 levels)
def zip_probe(path: Path, root_dirs: set[str]) -> dict:
    info: dict = {
        "entries": 0,
        "uncompressed": 0,
        "max_depth": 0,
        "top": [],
        "types": {},
        "has_git": False,
        "repo_markers": [],
        "handover_markers": 0,
        "nested_archives": 0,
        "og5_hits": [],
        "error": None,
        "names_sig": [],
    }
    names: list[tuple[str, int]] = []
    try:
        if path.suffix.lower() == ".bundle":
            info.update(
                kind_hint="GIT_BUNDLE",
                heads=git_readonly.bundle_heads(path, 20),
                has_git=True,
            )
            return info
        if zipfile.is_zipfile(path):
            with zipfile.ZipFile(path) as zf:
                names = [(i.filename, i.file_size) for i in zf.infolist()]
        elif tarfile.is_tarfile(path):
            with tarfile.open(path) as tf:
                names = [(m.name, m.size) for m in tf.getmembers()]
        else:
            info["error"] = "not a zip/tar (single gzip stream?)"
            return info
    except Exception as exc:  # corrupt or encrypted archives are data, not crashes
        info["error"] = f"{type(exc).__name__}: {exc}"[:200]
        return info
    tops, types = collections.Counter(), collections.Counter()
    sig = set()
    for n, size in names:
        n = n.replace("\\", "/")
        parts = [p for p in n.split("/") if p]
        if not parts:
            continue
        depth = len(parts)
        info["max_depth"] = max(info["max_depth"], depth)
        tops[parts[0]] += 1
        info["uncompressed"] += size
        if "/.git/" in f"/{n}" or n.endswith(".git/HEAD"):
            info["has_git"] = True
        ext = Path(n).suffix.lower()
        if ext:
            types[EXT_TO_TYPE.get(ext, ext)] += 1
        if ext in (".zip", ".gz", ".tar", ".7z"):
            info["nested_archives"] += 1
        if depth <= 5:
            low = "/".join(parts[1:]) if len(parts) > 1 else parts[0]
            sig.add(low.lower())
            if (
                any(
                    low.endswith(m.rstrip("/"))
                    or (m.endswith("/") and low.startswith(m))
                    for m in REPO_MARKERS
                )
                and depth <= 3
            ):
                info["repo_markers"].append(n)
            if HANDOVER_RX.search(parts[-1]):
                info["handover_markers"] += 1
    info["entries"] = len(names)
    info["top"] = [t for t, _ in tops.most_common(6)]
    info["types"] = dict(types.most_common(10))
    blob = " ".join(info["top"]).lower() + " " + path.name.lower()
    info["og5_hits"] = [
        r for r in OG5 if r.lower().replace("-", "_") in blob.replace("-", "_")
    ]
    generic = {
        "scripts",
        "data",
        "docs",
        "src",
        "tests",
        "agents",
        ".github",
        "config",
        "tools",
        "governance",
        "output",
        "github_repos",
        "uploads",
        "templates",
        "schemas",
        "reports",
        "_tmprepo",
        "core",
        "ci",
        "logs",
    }
    stem = path.name.split(".")[0]
    info["extracted_sibling"] = sorted(
        {t for t in info["top"] if t in root_dirs and t.lower() not in generic}
        | ({stem} & root_dirs)
    )
    info["repo_markers"] = info["repo_markers"][:8]
    info["names_sig"] = sorted(sig)[:4000]
    return info


def reverse_kahn(zips: list[dict]) -> None:
    """Edges older -> newer (same family stem, or >=60% shared entry set). Tips = sinks.
    Kahn's algorithm on the reversed graph peels layers from the tips: layer 0 = tip, 1 = its direct predecessor...

    TODO(kahn-owner): topological layering is owned by the hub, pipeline-automation-hub
    mission-control/jade_temple/devops/lifecycle.py::topo_layers(nodes, edges) (hub AGENTS.md, metric ownership).
    ABACUS has no pinned bridge to the hub yet, so this local layering stays until that bridge exists and the owner
    decides; then call topo_layers on the reversed edges here instead of peeling layers locally.
    """
    ss = _load_kernel(
        "set_similarity"
    )  # gg_MATH kernels/set_similarity.py, pinned in ggmath_bridge.PINS
    by_name = {z["name"]: z for z in zips}
    succ: dict[str, set[str]] = {z["name"]: set() for z in zips}
    sigs = {z["name"]: set(z["zip"].get("names_sig") or []) for z in zips}
    ordered = sorted(zips, key=lambda z: z["mtime"])
    for i, a in enumerate(ordered):
        for b in ordered[i + 1 :]:
            same_family = a["family"] == b["family"]
            sa, sb = sigs[a["name"]], sigs[b["name"]]
            overlap = ss.overlap(
                sa, sb
            )  # |a & b| / min(|a|, |b|), 0 when either is empty
            if same_family or (overlap >= 0.6 and min(len(sa), len(sb)) >= 5):
                succ[a["name"]].add(b["name"])
    # transitive reduction-lite: keep only the nearest successor per family to keep chains readable
    for n, s in succ.items():
        if len(s) > 1:
            nearest = min(s, key=lambda m: by_name[m]["mtime"])
            fam = {m for m in s if by_name[m]["family"] == by_name[n]["family"]}
            succ[n] = {nearest} | (s - fam)
    pred: dict[str, set[str]] = {n: set() for n in succ}
    for n, s in succ.items():
        for m in s:
            pred[m].add(n)
    outdeg = {n: len(s) for n, s in succ.items()}
    frontier = [n for n, d in outdeg.items() if d == 0]
    layer = 0
    while frontier:
        nxt = []
        for n in frontier:
            by_name[n]["kahn_layer"] = layer
            for p in pred[n]:
                outdeg[p] -= 1
                if outdeg[p] == 0:
                    nxt.append(p)
        frontier, layer = nxt, layer + 1
    for z in zips:
        z.setdefault(
            "kahn_layer", -1
        )  # -1 = in a cycle (identical mtimes); flag for a human
        z["successors"] = sorted(succ[z["name"]])
        z["predecessors"] = sorted(pred[z["name"]])
        zp = z["zip"]
        if (
            zp.get("kind_hint") == "GIT_BUNDLE"
            or zp.get("has_git")
            or len(zp.get("repo_markers", [])) >= 2
        ):
            kind = "REPO_SNAPSHOT"
        elif re.search(
            r"setup|plugin|installer|vsix|extension|node-v", z["name"], re.I
        ) or "exe" in str(zp.get("types")):
            kind = "INSTALLER_TOOL"
        elif HANDOVER_RX.search(z["name"]) or zp.get("handover_markers", 0) >= 1:
            kind = "HANDOVER"
        else:
            kind = "DATA_BUNDLE"
        z["zip_kind"] = kind
        if zp.get("extracted_sibling"):
            status = "EXTRACTED"
        elif z["kahn_layer"] > 0:
            status = "SUPERSEDED"
        elif z["kahn_layer"] < 0:
            status = "CYCLE_REVIEW"
        elif z["age_days"] < 60:
            status = "TIP_ACTIVE"
        else:
            status = "TIP_DORMANT"
        z["zip_status"] = status
        z["zip_next"] = {
            (
                "REPO_SNAPSHOT",
                "TIP_DORMANT",
            ): "ACTIVATE: compare with OG5 origin; land unique commits or park",
            ("REPO_SNAPSHOT", "TIP_ACTIVE"): "ACTIVATE: compare with OG5 origin now",
            (
                "HANDOVER",
                "TIP_DORMANT",
            ): "DEEP_READ: absorb manifest into owning repo, then archive",
            (
                "HANDOVER",
                "TIP_ACTIVE",
            ): "DEEP_READ: handover in flight; confirm receiving repo",
            (
                "INSTALLER_TOOL",
                "TIP_DORMANT",
            ): "ARCHIVE: installer/tool, not project content",
            (
                "INSTALLER_TOOL",
                "TIP_ACTIVE",
            ): "ARCHIVE: installer/tool, not project content",
        }.get(
            (kind, status),
            {
                "SUPERSEDED": "ARCHIVE: superseded by "
                + ", ".join(z["successors"][:2]),
                "EXTRACTED": "CHECK: extracted folder exists; diff then archive the zip",
                "CYCLE_REVIEW": "HUMAN: identical timestamps, order unknown",
            }.get(status, "DEEP_READ"),
        )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root-id", default="MI", choices=sorted(ROOTS))
    ap.add_argument("--no-hash", action="store_true")
    args = ap.parse_args()
    root, depth = ROOTS[args.root_id]
    hash_max = DEPTH[depth]["hash_max_bytes"]
    out = inv_dir(args.root_id)
    out.mkdir(parents=True, exist_ok=True)
    now = dt.datetime.now()
    tracked = git_tracked(root)
    # Guard G1: never follow links (junctions/symlinks such as .ssh, .aws, .azure, .gnupg) and never descend into any folder;
    # sensitive folder names are not even listed. OneDrive placeholders are file reparse points too, so only true links are skipped.
    entries = [
        e
        for e in os.scandir(root)
        if not e.is_symlink()
        and not (e.is_dir(follow_symlinks=False) and e.name.lower() in SENSITIVE_DIRS)
    ]
    root_dirs = {
        e.name for e in entries if e.is_dir(follow_symlinks=False) and not _is_link(e)
    }
    rows, other = [], collections.Counter()
    for name, p, st, location in estate_files(root, entries):
        base = (
            p.name
        )  # classify on the file's own name, never on the GG_/epic folder it was grouped into
        ext = Path(base).suffix.lower()
        if base.startswith("~$"):
            other["OFFICE_LOCKFILE"] += 1
            continue
        typ = EXT_TO_TYPE.get(ext)
        if not typ:
            other[ext or "(none)"] += 1
            continue
        age = (now - dt.datetime.fromtimestamp(st.st_mtime)).total_seconds() / 86400
        epic, repo, score, hits = classify_epic(base)
        attrs = getattr(st, "st_file_attributes", 0)
        cloud_only = bool(
            attrs & 0x400000 or attrs & 0x1000
        )  # OneDrive online-only: reading would download it
        magic = "cloud_only" if cloud_only else sniff(p)
        exp = EXPECT.get(typ)
        row = {
            "name": name,
            "type": typ,
            "letter": TYPE_LETTER[typ],
            "ext": ext,
            "bytes": st.st_size,
            "mtime": dt.datetime.fromtimestamp(st.st_mtime).isoformat(
                timespec="seconds"
            ),
            "age_days": round(age, 1),
            "staleness": staleness(age),
            "epic": epic,
            "og5_repo": repo,
            "epic_score": score,
            "epic_hits": " ".join(hits),
            "family": family_stem(base),
            "root_id": args.root_id,
            "cloud_only": cloud_only,
            "location": location,
            "magic": magic,
            "magic_ok": cloud_only
            or (
                exp is None
                or magic == exp
                or (typ == "XLSX" and ext == ".csv")
                or (
                    typ == "ZIP"
                    and magic in ("gzip", "gitbundle", "other")
                    and ext != ".zip"
                )
                or (typ == "VSDX" and ext in (".drawio", ".mmd"))
                or (ext == ".xps" and magic == "zip")
                or (ext == ".tar" and magic == "text")
            ),
            "git_tracked": tracked is None or name in tracked,
            "office_lock_present": (p.parent / ("~$" + base)).exists()
            or (p.parent / ("~$" + base[2:])).exists(),
            "copy_marker": bool(re.search(r"\(\d+\)", base)),
            "sha256": (
                ""
                if (args.no_hash or cloud_only or (hash_max and st.st_size > hash_max))
                else sha256(p)
            ),
        }
        if typ == "ZIP":
            row["zip"] = (
                zip_probe(p, root_dirs)
                if not cloud_only
                else {"error": "cloud_only", "top": [], "names_sig": []}
            )
            zepic = classify_epic(base, " ".join(row["zip"].get("top", [])))
            if zepic[2] > score:
                row.update(
                    epic=zepic[0],
                    og5_repo=zepic[1],
                    epic_score=zepic[2],
                    epic_hits=" ".join(zepic[3]),
                )
        rows.append(row)

    # duplicates by content (K-ANY-02 hash) and family lineage tips for every type
    by_sha = collections.defaultdict(list)
    for r in rows:
        if r["sha256"]:
            by_sha[r["sha256"]].append(r)
    for group in by_sha.values():
        if len(group) > 1:
            keep = max(group, key=lambda r: (not r["copy_marker"], r["mtime"]))
            for r in group:
                r["duplicate_of"] = "" if r is keep else keep["name"]
    fam = collections.defaultdict(list)
    for r in rows:
        fam[(r["type"], r["family"])].append(r)
    for (_, _), group in fam.items():
        group.sort(key=lambda r: r["mtime"])
        for i, r in enumerate(group):
            r["family_size"] = len(group)
            r["family_tip"] = i == len(group) - 1
    for r in rows:
        r.setdefault("duplicate_of", "")
        if r["duplicate_of"]:
            r["decision_hint"] = "DUPLICATE"
        elif not r["family_tip"]:
            r["decision_hint"] = "SUPERSEDED"
        elif r["staleness"] == "FROZEN":
            r["decision_hint"] = "STALE_ARCHIVE"
        else:
            r["decision_hint"] = "KEEP_CANONICAL" if r["epic"] != "E0_OTHER" else "PARK"

    zips = [r for r in rows if r["type"] == "ZIP"]
    reverse_kahn(zips)
    for z in zips:
        if z["zip_status"] == "SUPERSEDED":
            z["decision_hint"] = "SUPERSEDED"
        elif z["zip_next"].startswith("ACTIVATE"):
            z["decision_hint"] = "ACTIVATE_ZIP"

    # ---------------- write
    cols = [
        "letter",
        "type",
        "epic",
        "og5_repo",
        "name",
        "bytes",
        "mtime",
        "age_days",
        "staleness",
        "family",
        "family_size",
        "family_tip",
        "duplicate_of",
        "decision_hint",
        "git_tracked",
        "office_lock_present",
        "magic",
        "magic_ok",
        "epic_score",
        "epic_hits",
        "sha256",
    ]
    with (out / "root_inventory.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(
            sorted(rows, key=lambda r: (r["letter"], r["epic"], r["name"].lower()))
        )
    zip_out = [{k: v for k, v in z.items()} for z in zips]
    for z in zip_out:
        z["zip"] = {k: v for k, v in z["zip"].items() if k != "names_sig"}
    (out / "zip_reverse_kahn.json").write_text(
        json.dumps(
            {
                "schema": SCHEMA + "#zip",
                "generated": now.isoformat(timespec="seconds"),
                "zips": zip_out,
            },
            indent=1,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (out / "root_inventory.json").write_text(
        json.dumps(
            {
                "schema": SCHEMA,
                "generated": now.isoformat(timespec="seconds"),
                "root": str(root),
                "root_id": args.root_id,
                "depth": depth,
                "git_head": git_readonly.head(root),
                "rows": [{k: v for k, v in r.items() if k != "zip"} for r in rows],
                "not_human_facing": dict(other.most_common()),
            },
            indent=1,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    # ---------------- summary matrix
    epics = [e[0] for e in EPICS] + [OTHER_EPIC[0]]
    m = collections.Counter((r["type"], r["epic"]) for r in rows)
    mb = collections.Counter()
    for r in rows:
        mb[r["type"]] += r["bytes"]
    lines = [
        f"# {args.root_id} root ({root}) - binary estate inventory, depth={depth}",
        "",
        f"Generated {now:%Y-%m-%d %H:%M}. Read-only scan of the root only (folders not entered). "
        f"{len(rows)} human-facing files; {sum(other.values())} other root files not grouped.",
        "",
        "| Type | " + " | ".join(e.split("_", 1)[0] for e in epics) + " | Total | MB |",
        "|---|" + "---:|" * (len(epics) + 2),
    ]
    for letter, code, _, _ in TYPES:
        cnt = [m[(code, e)] for e in epics]
        lines.append(
            f"| {letter} {code} | "
            + " | ".join(str(c) for c in cnt)
            + f" | {sum(cnt)} | {mb[code] / 1e6:,.0f} |"
        )
    lines += [
        "",
        "Epic key: "
        + "; ".join(f"{e[0]} -> {e[1]}" for e in EPICS)
        + "; E0_OTHER -> unassigned",
        "",
    ]
    hints = collections.Counter(r["decision_hint"] for r in rows)
    lines += ["## Decision hints (E6, provisional)", ""] + [
        f"- {k}: {v}" for k, v in hints.most_common()
    ]
    zs = collections.Counter((z["zip_kind"], z["zip_status"]) for z in zips)
    lines += ["", "## ZIP reverse-Kahn", ""] + [
        f"- {k[0]} / {k[1]}: {v}" for k, v in sorted(zs.items())
    ]
    total_files = len(rows) + sum(other.values())
    lines += [
        "",
        "## What is not counted",
        "",
        f"Files at the top level: {total_files}. Grouped (human-facing types A-K): {len(rows)}. Excluded: {sum(other.values())}, by extension: "
        + ", ".join(f"{k} {v}" for k, v in other.most_common()),
        "Folders are never entered; links (junctions, symlinks) and sensitive folders (.ssh, .aws, .azure, .gnupg, _personal, "
        "_canonical_private) are skipped without reading or listing them.",
    ]
    lines += [
        "",
        f"Office lock file present (may be open; do not move): {sum(r['office_lock_present'] for r in rows)}",
        f"Tracked by git in this root (move only with git mv on a branch): {sum(r['git_tracked'] for r in rows)}",
        f"Bytes not matching extension (K-ANY-01): {sum(not r['magic_ok'] for r in rows)}",
    ]
    (out / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
