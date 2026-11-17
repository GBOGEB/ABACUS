"""Exact, type-preserving encoding of CoolProp PropsSI calls and outcomes.

Shared by the recorder (loaded at interpreter start through sitecustomize, so it
must stay dependency-free and import nothing from the repository) and by the
replay tool. Floats are stored with float.hex() so a replay sees bit-identical
inputs, and Python argument *types* are kept: CoolProp 8's nanobind binding
dispatches int literals to a different C++ path than floats, so replaying
`PropsSI("P", "T", 4.2, "Q", 0, "Helium")` with Q=0.0 would test the wrong code.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

SCHEMA = "abacus-coolprop-shadow/1.0.0"


class Unreplayable(ValueError):
    """An argument type the codec cannot rebuild faithfully."""


def _numpy():
    import numpy  # only needed when numpy values were actually seen

    return numpy


def encode(value: Any) -> list:
    if isinstance(value, bool):
        return ["bool", value]
    if type(value) is int:
        return ["int", value]
    if type(value) is float:
        return ["float", value.hex()]
    if type(value) is str:
        return ["str", value]
    if isinstance(value, (list, tuple)):
        return [type(value).__name__, [encode(item) for item in value]]
    module = type(value).__module__
    if module == "numpy":
        np = _numpy()
        if isinstance(value, np.ndarray):
            flat = [encode(item.item()) for item in value.reshape(-1)]
            return ["ndarray", str(value.dtype), list(value.shape), flat]
        if isinstance(value, np.floating):
            return ["npfloat", str(value.dtype), float(value).hex()]
        if isinstance(value, np.integer):
            return ["npint", str(value.dtype), int(value)]
    return ["repr", f"{module}.{type(value).__qualname__}", repr(value)]


def decode(item: list) -> Any:
    kind = item[0]
    if kind in ("bool", "int", "str"):
        return item[1]
    if kind == "float":
        return float.fromhex(item[1])
    if kind == "list":
        return [decode(x) for x in item[1]]
    if kind == "tuple":
        return tuple(decode(x) for x in item[1])
    if kind == "npfloat":
        return _numpy().dtype(item[1]).type(float.fromhex(item[2]))
    if kind == "npint":
        return _numpy().dtype(item[1]).type(item[2])
    if kind == "ndarray":
        np = _numpy()
        values = [decode(x) for x in item[3]]
        return np.array(values, dtype=item[1]).reshape(item[2])
    raise Unreplayable(f"cannot rebuild {item[1]}: {item[2]}")


def encode_call(args: tuple, kwargs: dict) -> str:
    payload = {"args": [encode(a) for a in args]}
    if kwargs:
        payload["kwargs"] = {k: encode(v) for k, v in sorted(kwargs.items())}
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def decode_call(key: str) -> tuple[tuple, dict]:
    payload = json.loads(key)
    args = tuple(decode(a) for a in payload["args"])
    kwargs = {k: decode(v) for k, v in payload.get("kwargs", {}).items()}
    return args, kwargs


def key_id(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:20]


def outcome_of_result(result: Any) -> list:
    return ["value", encode(result)]


def outcome_of_error(exc: BaseException) -> list:
    return ["error", type(exc).__name__, str(exc).strip()]
