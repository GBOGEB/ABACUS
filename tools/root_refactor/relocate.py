#!/usr/bin/env python3
"""Move loose root files in owner-approved waves without breaking links.

The relocation map (ROOT_RELOCATION_MAP.csv) is the single source of truth:
one row per moved file, old_path -> new_path, with its family, wave and JADE
root disposition. Plan: docs/repo-structure/ROOT_REFACTOR_PLAN.md.

    python tools/root_refactor/relocate.py apply --wave W1   # git mv + link rewrite
    python tools/root_refactor/relocate.py check             # invariants (also run by tests)

`apply` is idempotent. For every row of the wave it runs `git mv`, rewrites
relative Markdown/HTML links that resolve to the old path (in every tracked
document), and re-bases the moved file's own relative links to its new folder.
Plain-text mentions (tables, backticks, dated census snapshots) are history and
are left as written; the map resolves them. Links inside fenced code are kept.
Scripts, workflows and configs that name a moved file must be updated in the same
wave (MOVE_WITH_CONSUMER_REPLAY); `check` fails while one still names an old path.
A mention that is not the moved file (another folder's file of the same name, a
frozen log line) is acknowledged one consumer at a time, with a reason, in
ROOT_RELOCATION_MENTIONS.csv; an acknowledgement that no longer matches fails too.
Nothing is ever deleted.
"""
from __future__ import annotations

import argparse
import csv
import posixpath
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote, unquote

ROOT = Path(__file__).resolve().parents[2]
MAP = "docs_versioned/ROOT_RELOCATION_MAP.csv"
FIELDS = ["old_path", "new_path", "family", "wave", "disposition"]
MENTIONS = "docs_versioned/ROOT_RELOCATION_MENTIONS.csv"
MENTION_FIELDS = ["consumer_path", "old_path", "reason"]
FAMILIES = {"F1", "F2", "F3", "F4", "F5"}
DISPOSITIONS = {
    "ARCHIVE_PRESERVE_LINKS",
    "MOVE_WITH_CONSUMER_REPLAY",
    "LINK_ALIAS_FIRST",
}
DOC_EXT = (".md", ".markdown", ".html", ".htm")
CODE_EXT = (".py", ".sh", ".ps1", ".yml", ".yaml", ".toml", ".cfg", ".ini")
CODE_NAMES = {"Makefile", "Dockerfile"}

INLINE = re.compile(r"(\]\()(<[^>\n]+>|[^)\s]+)((?:\s+\"[^\"\n]*\")?\))")
REFDEF = re.compile(r"^(\s{0,3}\[[^\]\n]+\]:\s*)(<[^>\n]+>|\S+)", re.M)
HTML = re.compile(r"((?:href|src)=\")([^\"\n]+)(\")", re.I)
FENCE = re.compile(r"^\s*(```|~~~)")
EXTERNAL = re.compile(r"^(?:[a-z][a-z0-9+.-]*:|#|/|\{\{)", re.I)


def git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args],
        capture_output=True,
        check=True,
        text=True,
        encoding="utf-8",
    ).stdout


def load_map(root: Path = ROOT, name: str = MAP) -> list[dict]:
    path = root / name
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def validate_mentions(acks: list[dict], olds: set[str]) -> list[str]:
    errors = []
    for i, a in enumerate(acks, 2):
        if list(a) != MENTION_FIELDS:
            return [f"{MENTIONS}: header must be {','.join(MENTION_FIELDS)}"]
        if a["old_path"] not in olds:
            errors.append(f"{MENTIONS} line {i}: {a['old_path']!r} is not a mapped old_path")
        if not a["reason"].strip():
            errors.append(f"{MENTIONS} line {i}: reason is required")
    return errors


def split_target(raw: str) -> tuple[str, str, bool]:
    """Return (path part, '#frag' or '?query' suffix, was_angle_bracketed)."""
    angle = raw.startswith("<") and raw.endswith(">")
    t = raw[1:-1] if angle else raw
    cut = min([i for i in (t.find("#"), t.find("?")) if i >= 0], default=len(t))
    return t[:cut], t[cut:], angle


def resolve(src: str, target: str) -> str | None:
    """Repo-relative POSIX path a relative link in `src` points at, or None."""
    if not target or EXTERNAL.match(target):
        return None
    joined = posixpath.normpath(posixpath.join(posixpath.dirname(src), unquote(target)))
    return None if joined.startswith("..") or joined == "." else joined


def link_to(src: str, dest: str, encoded: bool, angle: bool) -> str:
    rel = posixpath.relpath(dest, posixpath.dirname(src) or ".")
    if encoded or (" " in rel and not angle):
        rel = quote(rel, safe="/._-~()")
    return f"<{rel}>" if angle else rel


def rewrite_links(text: str, src: str, new_src: str, moves: dict[str, str]) -> str:
    """Re-point relative links of document `src` (now living at `new_src`).

    A link is rewritten when its target moves, or when the document itself moves
    (so the same target needs a new relative path). Fenced code is left alone.
    """

    def fix(raw: str) -> str:
        path, suffix, angle = split_target(raw)
        old = resolve(src, path)
        if old is None:
            return raw
        dest = moves.get(old, old)
        if dest == old and new_src == src:
            return raw
        return link_to(new_src, dest, "%" in path, angle) + suffix

    out, fenced = [], False
    for line in text.splitlines(keepends=True):
        if FENCE.match(line):
            fenced = not fenced
            out.append(line)
            continue
        if not fenced:
            line = INLINE.sub(lambda m: m.group(1) + fix(m.group(2)) + m.group(3), line)
            line = REFDEF.sub(lambda m: m.group(1) + fix(m.group(2)), line)
            line = HTML.sub(lambda m: m.group(1) + fix(m.group(2)) + m.group(3), line)
        out.append(line)
    return "".join(out)


def links_to(text: str, src: str, targets: set[str]) -> list[str]:
    """Relative links in `src` (outside fenced code) that resolve into `targets`."""
    hits, fenced = [], False
    for line in text.splitlines():
        if FENCE.match(line):
            fenced = not fenced
            continue
        if fenced:
            continue
        for rx, grp in ((INLINE, 2), (REFDEF, 2), (HTML, 2)):
            for m in rx.finditer(line):
                p = resolve(src, split_target(m.group(grp))[0])
                if p in targets:
                    hits.append(p)
    return hits


def read(path: Path) -> str:
    return path.read_bytes().decode("utf-8", "surrogateescape")


def write(path: Path, text: str) -> None:
    path.write_bytes(text.encode("utf-8", "surrogateescape"))


def tracked_docs() -> list[str]:
    return [p for p in git("ls-files", "-z").split("\0") if p.lower().endswith(DOC_EXT)]


def validate_rows(rows: list[dict]) -> list[str]:
    errors, olds, news = [], set(), set()
    for i, r in enumerate(rows, 2):
        if list(r) != FIELDS:
            return [f"{MAP}: header must be {','.join(FIELDS)}"]
        old, new = r["old_path"], r["new_path"]
        if "/" in old:
            errors.append(f"line {i}: old_path {old!r} is not a root file")
        if "/" not in new or new.startswith(("/", "../")) or "\\" in new:
            errors.append(
                f"line {i}: new_path {new!r} must be a repo-relative sub-folder path"
            )
        if r["family"] not in FAMILIES:
            errors.append(f"line {i}: family {r['family']!r} not in {sorted(FAMILIES)}")
        if not re.fullmatch(r"W\d+[a-z]?", r["wave"]):
            errors.append(f"line {i}: wave {r['wave']!r} must look like W1 or W3a")
        if r["disposition"] not in DISPOSITIONS:
            errors.append(
                f"line {i}: disposition {r['disposition']!r} not in {sorted(DISPOSITIONS)}"
            )
        if old in olds or new in news:
            errors.append(f"line {i}: duplicate old_path or new_path")
        olds.add(old)
        news.add(new)
    return errors


def check(root: Path = ROOT) -> list[str]:
    rows = load_map(root)
    errors = validate_rows(rows)
    if errors:
        return errors
    olds = {r["old_path"] for r in rows}
    acks = load_map(root, MENTIONS)
    errors = validate_mentions(acks, olds)
    if errors:
        return errors
    acked = {(a["consumer_path"], a["old_path"]) for a in acks}
    for r in rows:
        if (root / r["old_path"]).exists():
            errors.append(
                f"{r['old_path']}: still at repo root (wave {r['wave']} not applied or file re-added)"
            )
        if not (root / r["new_path"]).is_file():
            errors.append(f"{r['new_path']}: relocation target missing")
    for doc in tracked_docs():
        path = root / doc
        if path.is_file():
            for old in links_to(read(path), doc, olds):
                errors.append(f"{doc}: link still points at moved root file {old}")
    seen = set()
    for src in tracked_code():
        path = root / src
        if path.is_file():
            for old in code_mentions(read(path), olds):
                seen.add((src, old))
                if (src, old) not in acked:
                    errors.append(
                        f"{src}: code or config still names moved root file {old}"
                    )
    for src, old in sorted(acked - seen):
        errors.append(
            f"{MENTIONS}: {src} no longer names {old}; remove the acknowledgement"
        )
    return errors


def code_mentions(text: str, olds: set[str]) -> list[str]:
    """Moved root names a script or config still uses as a bare root path (not `dir/name`)."""
    if not olds:
        return []
    bare = re.compile(
        r"(?<![\w./\\-])("
        + "|".join(map(re.escape, sorted(olds, key=len, reverse=True)))
        + r")(?![\w.-])"
    )
    return sorted(set(bare.findall(text)))


def tracked_code() -> list[str]:
    """Files that can open a root path at run time: scripts, workflows, build and tool configs."""
    return [
        p
        for p in git("ls-files", "-z").split("\0")
        if p.lower().endswith(CODE_EXT) or posixpath.basename(p) in CODE_NAMES
    ]


def apply(wave: str) -> int:
    rows = load_map()
    errors = validate_rows(rows)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    todo = {
        r["old_path"]: r["new_path"]
        for r in rows
        if r["wave"] == wave and (ROOT / r["old_path"]).exists()
    }
    if not todo:
        print(f"{wave}: nothing to move (already applied or no rows)")
        return 0
    # rewrite links first, while every document is still at its old path
    edited = 0
    for doc in tracked_docs():
        path = ROOT / doc
        if not path.is_file():
            continue
        text = read(path)
        new = rewrite_links(text, doc, todo.get(doc, doc), todo)
        if new != text:
            write(path, new)
            edited += 1
    for old, new in todo.items():
        (ROOT / new).parent.mkdir(parents=True, exist_ok=True)
        git("mv", "--", old, new)
    print(f"{wave}: moved {len(todo)} file(s); rewrote links in {edited} document(s)")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("apply").add_argument("--wave", required=True)
    sub.add_parser("check")
    args = ap.parse_args(argv)
    if args.cmd == "apply":
        return apply(args.wave)
    errors = check()
    for e in errors:
        print(e, file=sys.stderr)
    print(
        f"root relocation check: {len(load_map())} mapped file(s), {len(errors)} problem(s)"
    )
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
