"""Pinned bridge to the GBOGEB/gg_MATH kernels: the engines import the math, they never copy it.

gg_MATH is not a pip package. Each kernel is pinned in ``PINS`` by gg_MATH commit, path, git blob id and sha256.
``load(name)`` returns a module built from exactly those bytes, or raises ``KernelPinError`` (fail closed).

Where the bytes come from, in order:
  1. the cache, ``<ESTATE_HOME>/_ggmath/<name>-<blob>.py``, filled by an earlier verified load;
  2. ``GG_MATH_HOME``, a gg_MATH checkout: ``<GG_MATH_HOME>/<path>`` is used only if its bytes hash to the pinned
     blob id and sha256 (bytes with CRLF line ends are also tried with LF, for a checkout with core.autocrlf=true).
Nothing is downloaded and git is never run. The module is compiled from the verified bytes held in memory, never
from a file or bytecode cache that could change after the check.

To move a pin: check out the new gg_MATH commit in GG_MATH_HOME, run

    python -I DMAIC_V3/binary_engines/ggmath_bridge.py pin

and paste the printed entries into PINS (the command edits nothing). CI checks out gg_MATH at the pinned commit
(``.github/workflows/binary-engines.yml``); a test keeps that ref and these pins equal.
"""

from __future__ import annotations

import hashlib
import importlib.abc
import importlib.util
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import git_readonly  # noqa: E402
from estate_spec import ESTATE  # noqa: E402

REPO = "GBOGEB/gg_MATH"
PINS = {
    "set_similarity": {
        "commit": "198ec510dc0b929c28fee41c29ab3f9da8affada",
        "path": "kernels/set_similarity.py",
        "blob": "6a7050917991378fecc061fd1629c980808a4e8e",
        "sha256": "d9189b63bb9bedf2de4233fd07f4b4429efb53e6a2338716363de562a9caa60a",
    },
    "plane_geometry": {
        "commit": "198ec510dc0b929c28fee41c29ab3f9da8affada",
        "path": "kernels/plane_geometry.py",
        "blob": "93ac2bbd9faff963ddd373dc0b797642e06ede96",
        "sha256": "cbb2eda89fd4a2389b944e6aab0dec6c81d0dcaf8da4396dfd9d72211175b7df",
    },
}
CACHE = ESTATE / "_ggmath"


class KernelPinError(RuntimeError):
    """The pinned kernel bytes are not available here, or what is available does not match the pin."""


def blob_id(data: bytes) -> str:
    """git's object id of a blob (SHA-1 object format). It names the bytes; the sha256 pin is the integrity check."""
    return hashlib.sha1(
        b"blob %d\0" % len(data) + data, usedforsecurity=False
    ).hexdigest()


def verified(data: bytes, pin: dict) -> bytes | None:
    """The bytes that match ``pin`` (as given, or with CRLF line ends turned into LF), else None."""
    for candidate in (data, data.replace(b"\r\n", b"\n")):
        if (
            blob_id(candidate) == pin["blob"]
            and hashlib.sha256(candidate).hexdigest() == pin["sha256"]
        ):
            return candidate
    return None


def _cache_path(name: str) -> Path:
    return CACHE / f"{name}-{PINS[name]['blob'][:12]}.py"


def kernel_bytes(name: str) -> tuple[bytes, str]:
    """(verified bytes, where they came from) for the pinned kernel ``name``."""
    if name not in PINS:
        raise KernelPinError(
            f"no pin for gg_MATH kernel {name!r}; known: {', '.join(sorted(PINS))}"
        )
    pin = PINS[name]
    tried = []
    cache = _cache_path(name)
    if cache.is_file():
        data = verified(cache.read_bytes(), pin)
        if data is not None:
            return data, str(cache)
        tried.append(f"{cache} (does not match the pin)")
    home = os.environ.get("GG_MATH_HOME")
    if home:
        src = Path(home).expanduser() / pin["path"]
        if src.is_file():
            data = verified(src.read_bytes(), pin)
            if data is not None:
                cache.parent.mkdir(parents=True, exist_ok=True)
                tmp = cache.with_name(cache.name + ".tmp")
                tmp.write_bytes(data)
                os.replace(tmp, cache)
                return data, str(src)
            tried.append(
                f"{src} (blob {blob_id(src.read_bytes())[:12]}, pinned {pin['blob'][:12]})"
            )
        else:
            tried.append(f"{src} (missing)")
    else:
        tried.append("GG_MATH_HOME (not set)")
    raise KernelPinError(
        f"gg_MATH kernel {name!r} pinned at {REPO}@{pin['commit'][:12]}:{pin['path']} (blob {pin['blob'][:12]}) "
        f"is not available: tried {'; '.join(tried)}. Set GG_MATH_HOME to a gg_MATH checkout at that commit."
    )


class _VerifiedSourceLoader(importlib.abc.SourceLoader):
    """Compiles a module from bytes already verified in memory; never reads or writes a bytecode cache."""

    def __init__(self, origin: str, data: bytes) -> None:
        self._origin, self._data = origin, data

    def get_filename(self, fullname: str) -> str:
        return self._origin

    def get_data(self, path: str) -> bytes:
        return self._data


_LOADED: dict[str, object] = {}


def load(name: str):
    """The gg_MATH kernel module ``name``, built from the pinned bytes (cached per process)."""
    if name not in _LOADED:
        data, origin = kernel_bytes(name)
        modname = f"ggmath_{name}"
        loader = _VerifiedSourceLoader(origin, data)
        spec = importlib.util.spec_from_loader(modname, loader, origin=origin)
        module = importlib.util.module_from_spec(spec)
        sys.modules[modname] = module
        try:
            loader.exec_module(module)
        except BaseException:
            sys.modules.pop(modname, None)
            raise
        module.GG_MATH_PIN = dict(PINS[name], repo=REPO)
        _LOADED[name] = module
    return _LOADED[name]


def pin_entries(home: Path) -> dict:
    """PINS entries for the kernels as they are in the checkout ``home`` (bytes with LF line ends)."""
    out = {}
    commit = git_readonly.head(home)
    for name, pin in PINS.items():
        data = (home / pin["path"]).read_bytes().replace(b"\r\n", b"\n")
        out[name] = {
            "commit": commit,
            "path": pin["path"],
            "blob": blob_id(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }
    return out


def main(argv: list[str]) -> int:
    if argv[:1] == ["pin"]:
        home = os.environ.get("GG_MATH_HOME")
        if not home:
            print("set GG_MATH_HOME to a gg_MATH checkout at the commit to pin")
            return 2
        print(json.dumps(pin_entries(Path(home).expanduser()), indent=4))
        return 0
    for name in PINS:
        try:
            _, origin = kernel_bytes(name)
            print(f"OK    {name:15} {PINS[name]['blob'][:12]}  from {origin}")
        except KernelPinError as exc:
            print(f"FAIL  {exc}")
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
