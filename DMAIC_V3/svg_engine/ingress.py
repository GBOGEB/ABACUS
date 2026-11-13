"""Native SVG ingress (SVG-ENGINE W1).

The source drawing is parsed as XML: no OCR, no PDF-first extraction and no engineering inference.
Layer identity is the native ``id``; labels repeat across sub-systems and are never used as keys.
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from pathlib import Path
from zipfile import ZipFile

from lxml import etree

XINK = "{http://www.inkscape.org/namespaces/inkscape}"
PNS = {
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
}
TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.\-/+]{1,}")
CSS_URL = re.compile(r"url\(\s*(['\"]?)(.*?)\1\s*\)", re.IGNORECASE | re.DOTALL)


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha_file(p) -> str:
    return sha(Path(p).read_bytes())


def simple(x) -> str:
    """Local name of an element (namespace stripped); '' for comments and processing instructions."""
    return etree.QName(x).localname if isinstance(x.tag, str) else ""


def _safe_ref(value: str) -> bool:
    v = value.strip().lower()
    return not v or v.startswith(("#", "data:image/"))


def _check_css(text: str, where: str) -> None:
    """Reject CSS that can fetch: ``@import`` or any ``url(...)`` that is not a fragment or inline image.

    CSS escapes (``u\\72l(``) could hide either, so a backslash in a stylesheet or ``style`` fails closed.
    """
    if "@import" in text.lower() or (where == "style" and "\\" in text):
        raise ValueError("SVG_EXTERNAL_RESOURCE:" + where)
    for m in CSS_URL.finditer(text):
        if not _safe_ref(m.group(2)):
            raise ValueError("SVG_EXTERNAL_RESOURCE:" + where)


def validate_native_svg(root):
    """Fail closed for duplicate IDs and active/external references in inline SVG viewer input."""
    ids = set()
    for e in root.iter():
        if not isinstance(e.tag, str):
            continue
        kind = simple(e).lower()
        if kind in ("script", "foreignobject", "iframe", "object", "embed"):
            raise ValueError("SVG_UNSAFE_ELEMENT:" + kind)
        if kind == "style":
            _check_css("".join(e.itertext()), "style")
        identifier = e.get("id")
        if identifier:
            if identifier in ids:
                raise ValueError("SVG_DUPLICATE_ID:" + identifier)
            ids.add(identifier)
        for attr, val in e.attrib.items():
            key = etree.QName(attr).localname.lower()
            value = str(val).strip().lower()
            if key.startswith("on") and len(key) > 2:
                raise ValueError("SVG_EVENT_HANDLER:" + key)
            if key in ("href", "src") and not (
                value.startswith("#") or value.startswith("data:image/") or not value
            ):
                raise ValueError("SVG_EXTERNAL_RESOURCE:" + key)
            _check_css(str(val), key)
    return {"unique_ids": len(ids), "safe_inline_svg": True}


def parse_svg(data: bytes, *, validate: bool = True, huge_tree: bool = False):
    """Parse SVG bytes with entity resolution and network access disabled."""
    parser = etree.XMLParser(
        resolve_entities=False, no_network=True, recover=False, huge_tree=huge_tree
    )
    root = etree.fromstring(data, parser=parser)
    if validate:
        validate_native_svg(root)
    return root


def read_svg_bytes(path, member: str | None = None) -> bytes:
    """Read an SVG file, or one SVG member of a ZIP (``member`` or the ZIP's only ``*.svg``)."""
    p = Path(path)
    if member is None and p.suffix.lower() != ".zip":
        return p.read_bytes()
    with ZipFile(p) as z:
        if member is None:
            svgs = [n for n in z.namelist() if n.lower().endswith(".svg")]
            if len(svgs) != 1:
                raise ValueError(
                    f"SVG_MEMBER_AMBIGUOUS:{len(svgs)} svg members; pass member="
                )
            member = svgs[0]
        return z.read(member)


def load_svg(path, member: str | None = None, *, validate: bool = True):
    """Load and validate a source SVG. Returns ``(root, raw_bytes)``; hash the bytes for provenance."""
    data = read_svg_bytes(path, member)
    return parse_svg(data, validate=validate), data


def is_layer(e) -> bool:
    return simple(e) == "g" and e.get(XINK + "groupmode") == "layer"


def layer_items(root):
    """Every native Inkscape layer in document order, with its parent layer and its *own* source visibility."""
    result = []
    for x in root.iter():
        if is_layer(x):
            an = [a for a in x.iterancestors() if is_layer(a)]
            result.append(
                {
                    "id": x.get("id"),
                    "label": x.get(XINK + "label") or x.get("id"),
                    "parent_id": an[0].get("id") if an else None,
                    "level": len(an),
                    "path": list(
                        reversed([a.get(XINK + "label") or a.get("id") for a in an])
                    )
                    + [x.get(XINK + "label") or x.get("id")],
                    "source_visible": "display:none"
                    not in (x.get("style") or "").replace(" ", ""),
                }
            )
    return result


def tokens(text: str) -> Counter:
    return Counter(t.upper() for t in TOKEN.findall(text))


def own_text_tokens(layer) -> Counter:
    """Text tokens painted by this layer itself, excluding nested layers."""
    out = Counter()

    def walk(e):
        for c in e:
            if is_layer(c):
                continue
            if simple(c) == "text":
                out.update(tokens(" ".join("".join(c.itertext()).split())))
            else:
                walk(c)

    walk(layer)
    return out


def layer_tree_report(root, page_token_counters=()):
    """Native layer tree with source visibility, own text tokens and per-page token presence.

    ``page_token_counters``: one ``Counter`` of text tokens per page of a reference PDF (optional).
    Used to identify which layers an authored export showed on each page.
    """
    rows = []
    for e in root.iter():
        if not is_layer(e):
            continue
        anc = [a for a in e.iterancestors() if is_layer(a)]
        via_ordinary = [
            a
            for a in e.iterancestors()
            if simple(a) == "g"
            and not is_layer(a)
            and anc
            and a in set(anc[0].iterdescendants())
        ]
        t = own_text_tokens(e)
        n = sum(t.values())
        rows.append(
            {
                "id": e.get("id"),
                "label": e.get(XINK + "label"),
                "depth": len(anc),
                "source_visible": "display:none"
                not in (e.get("style") or "").replace(" ", ""),
                "own_text_tokens": n,
                "page_presence": [
                    round(sum((t & pg).values()) / n, 2) if n else None
                    for pg in page_token_counters
                ],
                "via_ordinary_groups": len(via_ordinary),
            }
        )
    return rows


def assert_operating_state_evidence(record):
    """Review-state inference guard; this is not an engineering state classifier.

    A valve state other than UNKNOWN needs evidence references and owner acceptance; colour alone never counts.
    """
    allowed = {"OPEN", "CLOSED", "MODULATING", "TRANSITION", "FAILED", "UNKNOWN"}
    state = record.get("state", "UNKNOWN")
    if state not in allowed:
        raise ValueError("INVALID_VALVE_STATE")
    if state != "UNKNOWN" and not record.get("evidence_refs"):
        raise ValueError("VALVE_STATE_WITHOUT_EVIDENCE")
    if state != "UNKNOWN" and record.get("owner_accepted") is not True:
        raise ValueError("VALVE_STATE_NOT_OWNER_ACCEPTED")
    return True
