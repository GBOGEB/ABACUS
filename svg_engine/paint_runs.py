"""Paint-order splitter (SVG-ENGINE W1).

Collects paint atoms in exact XML traversal order and splits subtrees at nested layer boundaries, so each
contiguous run of atoms has exactly one owning native layer. Re-assembling the runs in order reproduces the
source paint order; wrapping each run in its owner's optional-content group gives per-layer switches.
"""
from __future__ import annotations

import copy
import re

from lxml import etree

from .ingress import XINK, simple

_SKIP = ("defs", "metadata", "namedview", "title", "desc")
ROOT_OWNER = "__ROOT__"


def paint_atoms(root):
    """Return ``(atoms, runs)``. An atom is a paint subtree with no nested layer inside; a run is a maximal
    sequence of consecutive atoms with the same owner layer. Content outside any layer is owned by ``__ROOT__``."""
    atoms = []
    layerids = {x.get("id") for x in root.iter() if simple(x) == "g" and x.get(XINK + "groupmode") == "layer"}

    def has_nested_layer(e):
        return any(z is not e and z.get("id") in layerids and simple(z) == "g" for z in e.iter())

    def walk(e, path, owner, ancestor_ids):
        tag = simple(e)
        if tag in _SKIP or not tag:
            return
        if tag == "g" and e.get(XINK + "groupmode") == "layer":
            owner = e.get("id")
            ancestor_ids = ancestor_ids + [owner]
            for i, child in enumerate(e):
                walk(child, path + (i,), owner, ancestor_ids)
            return
        if tag == "svg" or (tag == "g" and has_nested_layer(e)):
            for i, child in enumerate(e):
                walk(child, path + (i,), owner, ancestor_ids)
            return
        atoms.append({"owner": owner if owner is not None else ROOT_OWNER, "path": path, "ancestors": ancestor_ids})

    walk(root, (), None, [])
    runs = []
    for atom in atoms:
        if not runs or atom["owner"] != runs[-1]["owner"]:
            runs.append({"owner": atom["owner"], "atoms": [], "ancestors": atom["ancestors"]})
        runs[-1]["atoms"].append(atom["path"])
    return atoms, runs


def isolated_svg(root, run) -> bytes:
    """SVG bytes containing only this run's paint atoms plus their ancestor context (groups, transforms,
    styles, ``defs``). Layers on the path are forced visible: visibility is applied later by optional content."""
    keep = set(run["atoms"])
    ancestors = set()
    for p in keep:
        for i in range(len(p) + 1):
            ancestors.add(p[:i])
    target = copy.deepcopy(root)

    def prune(e, p=()):
        if p in keep:
            return
        if p and simple(e) in ("defs", "metadata", "namedview"):
            return
        for i in reversed(range(len(e))):
            child = e[i]
            cp = p + (i,)
            if cp not in ancestors and simple(child) not in ("defs", "metadata", "namedview"):
                e.remove(child)
            else:
                prune(child, cp)
        if simple(e) == "g" and e.get(XINK + "groupmode") == "layer":
            st = e.get("style") or ""
            e.set("style", re.sub(r"display\s*:\s*none", "display:inline", st))

    prune(target)
    return etree.tostring(target, encoding="utf-8")
