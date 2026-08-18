"""
generate_artifact_registry.py -- idempotent SSOT generator for the project's
artifact registry. Re-run any time; it reads the actual working directory
(ground truth) rather than anyone's memory of what was built, groups files
into "families" by stripping the trailing _vN version suffix, flags the
newest file in each family as `is_latest`, and writes a single JSON file.

This exists because GBO asked for "recursive idempotent code and SSOT...
which makes editing and style more efficient" -- rather than a hand-typed
list (which drifts the moment a new version ships and nobody updates the
doc), this script IS the source of truth generation step. Re-run it after
every new deliverable; ENGINEERING_HANDOVER.md and any future session
should read ARTIFACT_REGISTRY.json, not re-derive this by hand.

No network calls, no randomness, no timestamps baked into logic (mtime is
read from disk, not generated) -- same inputs always produce the same
grouping/latest-flag output.
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
EXTS = {".xlsx", ".pptx", ".pdf", ".html", ".py", ".md", ".json", ".yaml", ".yml"}
VERSION_RE = re.compile(r"^(.*?)_(v\d+[a-z]?|v\d+_\d+)(\.[A-Za-z0-9]+)$")
SKIP_DIRS = {"__pycache__", "_f4check", "_rvcheck", "_theme_check", "charts", "extract",
             "extract_imgs", "imgs", "qa", "qa2", "qa3", "qa_bt0", "qa_bt1", "qa_bt5",
             "qa_bt5b", "qa_bt5c", "qa_full", "qa_test", "qa_v3", "qa_v3_full", "qa_v4",
             "qa_v5", "unpacked", "unpacked2", "uploads_v5", "xlsx_qa", "xlsx_qa2",
             "xlsx_qa3", "xlsx_qa4"}

def family_of(fname):
    m = VERSION_RE.match(fname)
    if m:
        return m.group(1) + m.group(3), m.group(2)
    return fname, None

def main():
    entries = []
    for fname in sorted(os.listdir(ROOT)):
        path = os.path.join(ROOT, fname)
        if not os.path.isfile(path):
            continue
        ext = os.path.splitext(fname)[1]
        if ext not in EXTS:
            continue
        fam, ver = family_of(fname)
        st = os.stat(path)
        entries.append({
            "file": fname, "family": fam, "version": ver,
            "ext": ext, "bytes": st.st_size, "mtime": st.st_mtime,
        })

    families = {}
    for e in entries:
        families.setdefault(e["family"], []).append(e)
    for fam, items in families.items():
        items.sort(key=lambda e: e["mtime"])
        for e in items:
            e["is_latest"] = False
        items[-1]["is_latest"] = True

    entries.sort(key=lambda e: (e["family"], e["mtime"]))
    out = {
        "generated_by": "generate_artifact_registry.py (idempotent, scans cwd)",
        "root": ROOT,
        "file_count": len(entries),
        "family_count": len(families),
        "families": {
            fam: {
                "latest": next(e["file"] for e in items if e["is_latest"]),
                "version_count": len(items),
                "versions": [e["file"] for e in items],
            }
            for fam, items in sorted(families.items())
        },
        "all_files": entries,
    }
    with open(os.path.join(ROOT, "ARTIFACT_REGISTRY.json"), "w") as f:
        json.dump(out, f, indent=2)
    print(f"wrote ARTIFACT_REGISTRY.json: {len(entries)} files, {len(families)} families")

if __name__ == "__main__":
    main()
