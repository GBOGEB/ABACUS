"""a10_guard.py - A10.8 tender-data guard for PUBLIC repos (ABACUS, CODEX, gg_MATH).

Blocks commits that add tender material: known tender folders, tender-like file names, or restricted
terms in the content. The restricted terms are stored only as salted SHA-256 hashes, so this file does
not itself publish bidder names.

  python a10_guard.py --staged     pre-commit hook mode (checks what you are about to commit)
  python a10_guard.py --head       every tracked file at HEAD
  python a10_guard.py --diff BASE  CI mode: files added or changed since BASE; falls back to --head

v3 (#2698): in --staged mode during a merge (MERGE_HEAD present) only the files whose staged content
differs from the merged-in parent are checked (the PR side plus conflict resolutions), so a merge of
main no longer re-checks files main already carries. Blobs are read with one `git archive` per chunk
of paths (each member verified against its blob id) instead of one `git cat-file -p` per file, and
paths are read NUL-separated.

v2 (5 Oct, review of PR ci/a10-guard):
  * Office/OpenDocument files (.docx .xlsx .pptx .odt ...) are unzipped and their XML text scanned;
    PDFs have their compressed streams inflated and scanned; other binary documents (.doc .xls .msg .zip ...)
    fail closed unless reviewed.
  * The baseline exempts a reviewed VERSION (salted hash of the git blob id), not a path: editing an
    allowed file re-checks it.
  * Whole files are scanned (no 400 KB cut); files over 50 MB fail closed.
  * Folder and name rules are case-insensitive.
"""

import hashlib
import io
import os
import re
import subprocess  # nosec B404
import sys
import tarfile
import unicodedata
import zipfile
import zlib

DIR_RULES = (
    "offers_itt/",
    "docs/qps_offer_rtm_evaluation/",
    "analytics/qps_cost_estimate_roundtrip/",
    "myrrha_handover/",
    "docs/myrrha_handover/",
    "tender_library/",
)
NAME_RX = re.compile(
    r"(tender|\bitt\b|_itt_|bidder|negotiat|nego\d|_nego|cost_estimate|qps[-_]lb|dko_|contractor_deviation|owner_acceptance|CONTRACT_Baseline)",
    re.I,
)
TERM_HASHES = set(
    [
        "15164c5978bc1506fe7a",
        "3fbce6526151efa6d59b",
        "5811518c57b69a801d24",
        "9fd22018f8afe644f2bc",
        "ab58fa323bc6a53a98ce",
        "bdde79b4bcf9ac067bf8",
        "c63c044470c2cd2e78f7",
        "cf2220465ba5181348a9",
        "d4cb548f83bc6ce9e49e",
        "ddb4efa05e290fd73466",
        "fd2070f475056ecfe75c",
    ]
)
TEXT_EXT = {
    ".md",
    ".txt",
    ".yaml",
    ".yml",
    ".json",
    ".csv",
    ".py",
    ".html",
    ".htm",
    ".js",
    ".toml",
    ".ini",
    ".xml",
    ".ps1",
    ".sh",
    ".cfg",
    ".tex",
    ".rst",
    ".ts",
    ".css",
    ".sql",
    ".m",
    ".r",
    ".ipynb",
    ".svg",
}
ZIP_DOC_EXT = {
    ".docx",
    ".docm",
    ".xlsx",
    ".xlsm",
    ".pptx",
    ".pptm",
    ".odt",
    ".ods",
    ".odp",
    ".vsdx",
}
CLOSED_EXT = {
    ".doc",
    ".xls",
    ".ppt",
    ".msg",
    ".eml",
    ".rtf",
    ".zip",
    ".7z",
    ".rar",
    ".gz",
    ".tar",
    ".mpp",
    ".vsd",
    ".pages",
    ".numbers",
    ".key",
}
MAX_BYTES = 50 * 1024 * 1024
ALLOW_FILE = ".a10_guard_allow"  # one entry per line: salted hash of a reviewed blob id (or of a path: legacy)
SELF = ("tools/a10_guard.py", "a10_guard.py", ALLOW_FILE)


def git(*a):
    return subprocess.run(["git", *a], capture_output=True).stdout  # nosec B603 B607


def git_z(*a):
    """Run a git command that takes -z and return its NUL-separated fields."""
    out = git(a[0], "-z", *a[1:]).decode("utf-8", "replace")
    return [f for f in out.split("\0") if f]


def index_ids(*a):
    """Map path -> blob id from `ls-files -s` or `ls-tree -r` output (-z)."""
    ids = {}
    for entry in git_z(*a):
        meta, p = entry.split("\t", 1)
        ids[p] = meta.split()[-2 if a[0] == "ls-files" else 2]
    return ids


# Attributes are read from the empty tree, so export-ignore, export-subst, ident, eol and
# filter attributes in the repository cannot hide or alter what the archive returns.
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"


def chunks(items, max_chars=6000, max_items=200):
    """Split (path, blob id) pairs so each git command line stays short (Windows limit)."""
    batch, size = [], 0
    for item in items:
        if batch and (size + len(item[0]) > max_chars or len(batch) >= max_items):
            yield batch
            batch, size = [], 0
        batch.append(item)
        size += len(item[0]) + 3
    if batch:
        yield batch


def read_blobs(tree, items):
    """Yield the content of each (path, blob id) pair, in order.

    One `git archive` per chunk replaces one `git cat-file -p` per file, which on a 1000-file
    merge spent minutes spawning processes (#2698). With no attributes and no eol conversion
    the archive member is the raw blob; a path missing from the archive (or a git older than
    2.40 without --attr-source) is read exactly with `git cat-file -p`.
    """
    for batch in chunks(items):
        raw = git(
            "--attr-source=" + EMPTY_TREE,
            "-c",
            "core.autocrlf=false",
            "--literal-pathspecs",
            "archive",
            "--format=tar",
            tree,
            "--",
            *[p for p, _ in batch],
        )
        members = {}
        try:
            with tarfile.open(fileobj=io.BytesIO(raw)) as tar:
                for member in tar:
                    if member.isfile():
                        members[member.name] = tar.extractfile(member).read()
        except tarfile.TarError:
            members = {}
        for p, bid in batch:
            data = members.get(p)
            if data is None:
                data = git("cat-file", "-p", bid)
            yield data


def read_merge_heads():
    """Every commit in MERGE_HEAD (one per merged parent; several for an octopus merge)."""
    if not git_ok("rev-parse", "-q", "--verify", "MERGE_HEAD"):
        return []
    path = (
        git("rev-parse", "--git-path", "MERGE_HEAD").decode("utf-8", "replace").strip()
    )
    try:
        with open(path, encoding="ascii") as f:
            heads = [line.split()[0] for line in f if line.strip()]
    except (OSError, UnicodeDecodeError, IndexError):
        heads = []
    return heads or ["MERGE_HEAD"]


def git_ok(*a):
    return subprocess.run(["git", *a], capture_output=True).returncode == 0  # nosec


def normalize(text):
    """NFKC-fold and drop invisible format characters (zero-width joiners etc.)."""
    text = unicodedata.normalize("NFKC", text)
    return "".join(c for c in text if unicodedata.category(c) != "Cf")


def decode_text(data):
    """Strict decode: UTF-8 (BOM optional) or BOM-marked UTF-16/32.

    Returns None for anything else, including NUL-padded text (BOM-less
    UTF-16), so the caller fails closed instead of replacement-decoding.
    """
    for bom, enc in (
        (b"\xff\xfe\x00\x00", "utf-32"),
        (b"\x00\x00\xfe\xff", "utf-32"),
        (b"\xff\xfe", "utf-16"),
        (b"\xfe\xff", "utf-16"),
    ):
        if data.startswith(bom):
            try:
                return data.decode(enc)
            except UnicodeDecodeError:
                return None
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return None
    return None if "\x00" in text else text


def hit_terms(text):
    words = re.findall(r"[a-z0-9]+", normalize(text).lower())
    for n in (1, 2, 3):
        for i in range(len(words) - n + 1):
            if (
                hashlib.sha256(
                    ("a10|" + " ".join(words[i : i + n])).encode()
                ).hexdigest()[:20]
                in TERM_HASHES
            ):
                return True
    return False


def doc_text(ext, data):
    """Return scannable text, or None when the format cannot be inspected (fail closed)."""
    if ext in ZIP_DOC_EXT:
        try:
            z = zipfile.ZipFile(io.BytesIO(data))
            parts = []
            for n in z.namelist():
                if n.endswith(".xml"):
                    xml = decode_text(z.read(n))
                    if xml is None:
                        return None
                    parts.append(re.sub(r"<[^>]+>", " ", xml))
            return " ".join(parts)
        except (zipfile.BadZipFile, KeyError, RuntimeError):
            return None
    if ext == ".pdf":
        parts = [data.decode("latin-1")]
        for m in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", data, re.S):
            try:
                parts.append(zlib.decompress(m.group(1)).decode("latin-1"))
            except zlib.error:
                # Some PDF streams are not zlib data; skip them and keep scanning.
                continue
        return " ".join(parts)
    return decode_text(data)


def reason(path, data):
    """Why this file looks like tender material, or '' if it does not."""
    low = path.replace("\\", "/").lower()
    if low.startswith(DIR_RULES):
        return "tender folder"
    if NAME_RX.search(path):
        return "tender-like name"
    if data is None:
        return ""
    ext = os.path.splitext(low)[1]
    if len(data) > MAX_BYTES:
        return "too large to inspect (fail closed)"
    if ext in CLOSED_EXT:
        return "binary document that cannot be inspected (fail closed)"
    if ext in TEXT_EXT or ext in ZIP_DOC_EXT or ext == ".pdf":
        text = doc_text(ext, data)
        if text is None:
            if ext in TEXT_EXT:
                return "unsupported text encoding (fail closed; save as UTF-8)"
            return "document that cannot be opened (fail closed)"
        if hit_terms(text):
            return "restricted term in content"
    return ""


def blob_key(blob_id):
    return hashlib.sha256(("a10b|" + blob_id).encode()).hexdigest()[:20]


def path_key(p):
    return hashlib.sha256(("a10p|" + p).encode()).hexdigest()[:20]


def main():
    staged = "--staged" in sys.argv
    base = (
        sys.argv[sys.argv.index("--diff") + 1]
        if "--diff" in sys.argv and sys.argv.index("--diff") + 1 < len(sys.argv)
        else None
    )
    if base and (
        set(base) <= {"0"} or not git_ok("cat-file", "-e", base + "^{commit}")
    ):
        print(
            f"a10_guard: base {base[:12]} not usable, checking every tracked file instead"
        )
        base = None
    allow = set()
    if os.path.exists(ALLOW_FILE):
        with open(ALLOW_FILE, encoding="utf-8") as f:
            allow = {
                line.strip() for line in f if line.strip() and not line.startswith("#")
            }
    if staged:
        merge_heads = read_merge_heads()
        if merge_heads:
            # Merge commit (#2698): check only what differs from every merged-in parent, i.e.
            # the PR side and conflict resolutions. For an octopus merge a file inherited
            # unchanged from any one parent is skipped.
            changed = None
            for head in merge_heads:
                differs = set(
                    git_z("diff", "--cached", "--name-only", "--diff-filter=ACMR", head)
                )
                changed = differs if changed is None else changed & differs
            paths = sorted(changed)
        else:
            paths = git_z("diff", "--cached", "--name-only", "--diff-filter=ACMR")
        ids = index_ids("ls-files", "-s")
    else:
        if base:
            paths = git_z("diff", "--name-only", "--diff-filter=ACMR", base + "...HEAD")
        else:
            paths = git_z("ls-files")
        ids = index_ids("ls-tree", "-r", "HEAD")
    bad = []
    todo = []
    for p in paths:
        if p in SELF or p.startswith(".githooks/"):
            continue
        bid = ids.get(p, "")
        if (bid and blob_key(bid) in allow) or path_key(p) in allow:
            continue
        if not bid:
            why = reason(p, None)
            if why:
                bad.append((p, why))
            continue
        todo.append((p, bid))
    tree = git("write-tree").decode().strip() if staged else "HEAD"
    for (p, _), data in zip(todo, read_blobs(tree, todo)):
        why = reason(p, data)
        if why:
            bad.append((p, why))
    for p, why in bad[:50]:
        print(f"  BLOCK  {p}   ({why})")
    if bad:
        print(
            f"a10_guard: {len(bad)} file(s) look like tender material. Move them to the PRIVATE cryoplant-project, "
            f"or have the version reviewed and its hash added to {ALLOW_FILE}."
        )
        sys.exit(1)
    print(f"a10_guard: OK ({len(paths)} files checked)")


if __name__ == "__main__":
    main()
