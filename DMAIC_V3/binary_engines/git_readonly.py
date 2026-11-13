"""Read git metadata from disk without running git: HEAD, tracked paths, bundle heads.

The estate readers only need three facts about a folder that may be a git checkout. Reading the files directly
means an inventory can never write into the checkout: no auto-gc, no lazy fetch from a partial clone, no lock
files. Anything this module does not understand (a split or sparse index, the reftable ref store, an unknown index
version) is reported as unknown (``None`` or ``""``), and callers fail closed.

Formats: Documentation/gitformat-index.txt (index v2-v4) and gitformat-bundle.txt (bundle v2/v3) in git.
"""

from __future__ import annotations

import re
import struct
from pathlib import Path

_SHA_RX = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")
_BUNDLE_SIGNATURES = (b"# v2 git bundle\n", b"# v3 git bundle\n")
_MAX_HEADER_LINES = 100_000


def find_repo(start: Path) -> tuple[Path, Path] | None:
    """(work tree top, git dir) of the repository that contains ``start``, or None outside any repository."""
    start = Path(start).resolve()
    for folder in (start, *start.parents):
        dot = folder / ".git"
        if dot.is_dir():
            return folder, dot
        if dot.is_file():  # linked worktree or submodule: "gitdir: <path>"
            text = dot.read_text("utf-8", "replace").strip()
            if not text.startswith("gitdir:"):
                return None
            gitdir = Path(text[len("gitdir:") :].strip())
            return (
                folder,
                (gitdir if gitdir.is_absolute() else folder / gitdir).resolve(),
            )
    return None


def _common_dir(gitdir: Path) -> Path:
    """The shared git dir of a linked worktree (its ``commondir`` file), else ``gitdir`` itself."""
    common = gitdir / "commondir"
    if common.is_file():
        rel = Path(common.read_text("utf-8", "replace").strip())
        return (rel if rel.is_absolute() else gitdir / rel).resolve()
    return gitdir


def _hash_length(common: Path) -> int:
    config = common / "config"
    text = config.read_text("utf-8", "replace") if config.is_file() else ""
    return 32 if re.search(r"(?im)^\s*objectformat\s*=\s*sha256\s*$", text) else 20


def head(start: Path) -> str:
    """Commit id at HEAD of the repository containing ``start``; "" when outside a repository or unknown."""
    found = find_repo(start)
    if not found:
        return ""
    gitdir = found[1]
    common = _common_dir(gitdir)
    head_file = gitdir / "HEAD"
    if not head_file.is_file():
        return ""
    value = head_file.read_text("utf-8", "replace").strip()
    if not value.startswith("ref:"):
        return value if _SHA_RX.fullmatch(value) else ""
    ref = value[len("ref:") :].strip()
    for base in (gitdir, common):
        loose = base / ref
        if loose.is_file():
            sha = loose.read_text("utf-8", "replace").strip()
            return sha if _SHA_RX.fullmatch(sha) else ""
    packed = common / "packed-refs"
    if packed.is_file():
        for line in packed.read_text("utf-8", "replace").splitlines():
            sha, _, name = line.partition(" ")
            if name.strip() == ref and _SHA_RX.fullmatch(sha):
                return sha
    return ""  # unborn branch or a ref store this reader does not know (reftable)


def _varint(data: bytes, pos: int) -> tuple[int, int]:
    """git's offset varint (index v4 path prefix lengths)."""
    byte = data[pos]
    pos += 1
    value = byte & 0x7F
    while byte & 0x80:
        byte = data[pos]
        pos += 1
        value = ((value + 1) << 7) | (byte & 0x7F)
    return value, pos


def index_paths(gitdir: Path) -> set[str] | None:
    """Every path in the index of ``gitdir`` ('/'-separated, relative to the work tree top).

    An empty set when there is no index yet; None when the index cannot be read completely.
    """
    index = gitdir / "index"
    if not index.is_file():
        return set()
    data = index.read_bytes()
    hash_len = _hash_length(_common_dir(gitdir))
    if len(data) < 12 + hash_len or data[:4] != b"DIRC":
        return None
    version, count = struct.unpack(">II", data[4:12])
    if version not in (2, 3, 4):
        return None
    pos, previous, names = 12, b"", set()
    fixed = 40 + hash_len  # stat data + object id
    try:
        for _ in range(count):
            start = pos
            pos += fixed
            (flags,) = struct.unpack(">H", data[pos : pos + 2])
            pos += 2
            if flags & 0x4000:  # extended flags (v3 and later)
                if version < 3:
                    return None
                pos += 2
            if version == 4:
                strip, pos = _varint(data, pos)
                end = data.index(b"\0", pos)
                if strip > len(previous):
                    return None
                name = previous[: len(previous) - strip] + data[pos:end]
                pos = end + 1
            else:
                end = data.index(b"\0", pos)
                name = data[pos:end]
                pos = start + (
                    (end - start + 8) & ~7
                )  # 1-8 NUL bytes pad the entry to a multiple of 8
            previous = name
            names.add(name.decode("utf-8", "replace"))
        # extensions: a split index keeps its entries in another file, a sparse index folds directories
        while pos + 8 <= len(data) - hash_len:
            signature = data[pos : pos + 4]
            (size,) = struct.unpack(">I", data[pos + 4 : pos + 8])
            if signature in (b"link", b"sdir"):
                return None
            pos += 8 + size
    except (ValueError, struct.error, IndexError):
        return None
    return names


def tracked_paths(start: Path) -> set[str] | None:
    """Paths under ``start`` that git tracks, relative to ``start`` ('/'-separated).

    An empty set outside any repository; None when ``start`` is in a repository whose index cannot be read
    (callers then treat every file as tracked).
    """
    found = find_repo(start)
    if not found:
        return set()
    top, gitdir = found
    names = index_paths(gitdir)
    if names is None:
        return None
    prefix = Path(start).resolve().relative_to(top).as_posix()
    if prefix in ("", "."):
        return names
    return {n[len(prefix) + 1 :] for n in names if n.startswith(prefix + "/")}


def bundle_heads(path: Path, limit: int = 20) -> list[str]:
    """The ref lines ("<id> <refname>") of a git bundle header, like ``git bundle list-heads``; [] if not a bundle."""
    out: list[str] = []
    with Path(path).open("rb") as fh:
        if fh.readline(64) not in _BUNDLE_SIGNATURES:
            return out
        for _ in range(_MAX_HEADER_LINES):
            line = fh.readline(4096)
            if line in (b"\n", b""):
                break  # the blank line ends the header; the pack follows
            text = line.decode("utf-8", "replace").rstrip("\n")
            if text.startswith(("-", "@")):
                continue  # prerequisites (-) and v3 capabilities (@) are not heads
            if len(out) < limit:
                out.append(text)
    return out
