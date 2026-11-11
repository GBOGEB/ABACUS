"""Record every CoolProp PropsSI call made by any Python process.

Active only when COOLPROP_SHADOW_RECORD_DIR is set and this directory is on
PYTHONPATH, which the coolprop-next-shadow workflow does for its record job
only. Loading at interpreter start (instead of as a pytest plugin) also covers
pytest-xdist workers and model CLIs that tests launch as subprocesses.

The wrapper is transparent: it returns CoolProp's result, or re-raises its
exception, unchanged. Each distinct call is appended to this process's own
JSONL file the first time it is seen, so nothing is lost if a worker exits
without running atexit handlers.
"""

from __future__ import annotations

import atexit
import functools
import importlib.abc
import json
import os
import platform
import sys
import uuid

_DIR = os.environ.get("COOLPROP_SHADOW_RECORD_DIR")
_TARGET = "CoolProp.CoolProp"


def _install() -> None:
    import coolprop_shadow_codec as codec

    os.makedirs(_DIR, exist_ok=True)
    path = os.path.join(_DIR, f"calls-{os.getpid()}-{uuid.uuid4().hex[:8]}.jsonl")
    seen: dict[str, dict] = {}
    state = {"handle": None}

    def write(record: dict) -> None:
        if state["handle"] is None:
            state["handle"] = open(path, "a", encoding="utf-8")
        state["handle"].write(json.dumps(record, sort_keys=True) + "\n")
        state["handle"].flush()

    def caller() -> str:
        frame = sys._getframe(2)
        while frame is not None and frame.f_code.co_filename == __file__:
            frame = frame.f_back
        if frame is None:
            return "?"
        module = frame.f_globals.get("__name__", "?")
        return f"{module}:{frame.f_lineno}"

    def wrap(original):
        @functools.wraps(original)
        def PropsSI(*args, **kwargs):  # noqa: N802 - mirrors CoolProp's name
            key = codec.encode_call(args, kwargs)
            try:
                result = original(*args, **kwargs)
            except Exception as exc:
                note(key, codec.outcome_of_error(exc))
                raise
            note(key, codec.outcome_of_result(result))
            return result

        PropsSI.__coolprop_shadow__ = True
        return PropsSI

    def note(key: str, outcome: list) -> None:
        entry = seen.get(key)
        if entry is None:
            import CoolProp

            seen[key] = {"count": 1, "outcome": outcome}
            if len(seen) == 1:
                write(
                    {
                        "header": {
                            "schema": codec.SCHEMA,
                            "coolprop": getattr(CoolProp, "__version__", "?"),
                            "python": platform.python_version(),
                            "platform": platform.platform(),
                        }
                    }
                )
            write(
                {
                    "key": key,
                    "id": codec.key_id(key),
                    "outcome": outcome,
                    "site": caller(),
                }
            )
            return
        entry["count"] += 1
        if entry["outcome"] != outcome and not entry.get("unstable"):
            entry["unstable"] = True
            write({"unstable": codec.key_id(key), "outcome": outcome})

    def flush_counts() -> None:
        counts = {
            codec.key_id(k): v["count"] for k, v in seen.items() if v["count"] > 1
        }
        if counts:
            write({"counts": counts})
        if state["handle"] is not None:
            state["handle"].close()

    atexit.register(flush_counts)

    def patch(module) -> None:
        current = getattr(module, "PropsSI", None)
        if current is not None and not getattr(current, "__coolprop_shadow__", False):
            module.PropsSI = wrap(current)

    class Finder(importlib.abc.MetaPathFinder):
        def find_spec(self, name, path=None, target=None):
            if name != _TARGET:
                return None
            for finder in sys.meta_path:
                if finder is self or not hasattr(finder, "find_spec"):
                    continue
                spec = finder.find_spec(name, path, target)
                if spec is not None and spec.loader is not None:
                    original_exec = spec.loader.exec_module

                    def exec_module(module, _exec=original_exec):
                        _exec(module)
                        patch(module)

                    spec.loader.exec_module = exec_module
                    return spec
            return None

    if _TARGET in sys.modules:
        patch(sys.modules[_TARGET])
    else:
        sys.meta_path.insert(0, Finder())


if _DIR:
    try:
        _install()
    except Exception as exc:  # never break the interpreter that loads us
        sys.stderr.write(f"coolprop-shadow recorder disabled: {exc!r}\n")
