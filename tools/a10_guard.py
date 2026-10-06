"""a10_guard.py - A10.8 tender-data guard for PUBLIC repos (ABACUS, CODEX, gg_MATH).

Blocks commits that add tender material: known tender folders, tender-like file names, or restricted
terms in the content. The restricted terms are stored only as salted SHA-256 hashes, so this file does
not itself publish bidder names.

  python a10_guard.py --staged     pre-commit hook mode (checks what you are about to commit)
  python a10_guard.py --head       every tracked file at HEAD
  python a10_guard.py --diff BASE  CI mode: files added or changed since BASE; falls back to --head

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


def git_ok(*a):
    return subprocess.run(["git", *a], capture_output=True).returncode == 0  # nosec


def hit_terms(text):
    words = re.findall(r"[a-z0-9]+", text.lower())
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
            return " ".join(
                re.sub(r"<[^>]+>", " ", z.read(n).decode("utf-8", "replace"))
                for n in z.namelist()
                if n.endswith(".xml")
            )
        except (zipfile.BadZipFile, KeyError, RuntimeError):
            return None
    if ext == ".pdf":
        parts = [data.decode("latin-1")]
        for m in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", data, re.S):
            try:
                parts.append(zlib.decompress(m.group(1)).decode("latin-1"))
            except zlib.error:
                pass
        return " ".join(parts)
    return data.decode("utf-8", "replace")


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
        allow = {
            l.strip()
            for l in open(ALLOW_FILE, encoding="utf-8")
            if l.strip() and not l.startswith("#")
        }
    if staged:
        paths = (
            git("diff", "--cached", "--name-only", "--diff-filter=ACMR")
            .decode("utf-8", "replace")
            .splitlines()
        )
        ids = {}
        for line in git("ls-files", "-s").decode("utf-8", "replace").splitlines():
            meta, p = line.split("\t", 1)
            ids[p] = meta.split()[1]
    else:
        if base:
            paths = (
                git("diff", "--name-only", "--diff-filter=ACMR", base + "...HEAD")
                .decode("utf-8", "replace")
                .splitlines()
            )
        else:
            paths = git("ls-files").decode("utf-8", "replace").splitlines()
        ids = {}
        for line in (
            git("ls-tree", "-r", "HEAD").decode("utf-8", "replace").splitlines()
        ):
            meta, p = line.split("\t", 1)
            ids[p] = meta.split()[2]
    bad = []
    for p in paths:
        if p in SELF or p.startswith(".githooks/"):
            continue
        bid = ids.get(p, "")
        if (bid and blob_key(bid) in allow) or path_key(p) in allow:
            continue
        data = git("cat-file", "-p", bid) if bid else None
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
