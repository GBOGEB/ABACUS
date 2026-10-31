"""Read-only, fail-closed OOXML style/format input probe for ABACUS.

The caller supplies real .docx/.xlsx/.pptx files from an authorized source.
No macros, embedded OLE, external relations, byte payloads, or document text
are executed, exported or copied. This is observational style evidence,
not a document editor, authority transfer, or security approval.

No third-party dependencies. Compatible with Python 3.9+.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import posixpath
import re
import stat
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from pathlib import Path

SCHEMA = "abacus.office-style-evidence.v1"
MAX_MEMBERS = 2048
MAX_MEMBER_BYTES = 12 * 1024 * 1024
MAX_TOTAL_BYTES = 64 * 1024 * 1024
MAX_COMPRESSION_RATIO = 250
MAX_SOURCE_BYTES = 64 * 1024 * 1024
VALID_SOURCE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,95}$")
SLIDE_RE = re.compile(r"^ppt/slides/slide([1-9][0-9]*)\.xml$")
Q = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}
ALLOWED = {
    ".docx": ("docx", "word/document.xml"),
    ".xlsx": ("xlsx", "xl/workbook.xml"),
    ".pptx": ("pptx", "ppt/presentation.xml"),
}
FORBIDDEN = (
    "vbaproject",
    "/activex/",
    "/embeddings/",
    "/externallinks/",
    "oleobject",
    "customui/",
    "/macros/",
)


def _tag(prefix, name):
    return "{" + Q[prefix] + "}" + name


def _attr(el, prefix, name, default=None):
    return el.get(_tag(prefix, name), default) if el is not None else default


def _json_hash(payload):
    return hashlib.sha256(
        json.dumps(
            payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def _is_true(value):
    return value not in (None, "0", "false", "False", "off")


def _bounded_counter(counter, cap=40):
    return dict(sorted(counter.items(), key=lambda x: (-x[1], x[0]))[:cap])


def _fill(element):
    if element is None:
        return None
    color = element.find("./a:srgbClr", Q)
    if color is not None:
        value = color.get("val", "")
        return "#" + value.upper() if re.fullmatch(r"[0-9a-fA-F]{6}", value) else None
    color = element.find("./a:schemeClr", Q)
    if color is not None:
        return "theme:" + color.get("val", "unknown")
    color = element.find("./a:sysClr", Q)
    if color is not None:
        return "#" + color.get("lastClr", "").upper() if color.get("lastClr") else None
    return None


def _theme(package, member):
    if member not in package:
        return {"status": "ABSENT", "colors": {}, "fonts": {}}
    root = package.xml(member)
    colors = {}
    scheme = root.find(".//a:clrScheme", Q)
    if scheme is not None:
        for child in scheme:
            color = _fill(child)
            if color:
                colors[child.tag.rsplit("}", 1)[-1]] = color
    fonts = {}
    for variant in ("majorFont", "minorFont"):
        latin = root.find(f".//a:fontScheme/a:{variant}/a:latin", Q)
        if latin is not None:
            fonts[variant] = latin.get("typeface")
    return {"status": "OBSERVED", "colors": colors, "fonts": fonts}


class OfficePackage:
    """Open an Office archive without extracting anything, rejecting risky inputs."""

    def __init__(self, file_path, extension):
        self.path = Path(file_path)
        if extension not in ALLOWED or self.path.suffix.lower() != extension:
            raise ValueError("unsupported Office type/extension mismatch")
        if not self.path.is_file():
            raise ValueError("input file missing")
        if self.path.stat().st_size > MAX_SOURCE_BYTES:
            raise ValueError("source exceeds bounded input limit")
        if not zipfile.is_zipfile(self.path):
            raise ValueError("input is not an Office ZIP package")
        self.archive = zipfile.ZipFile(self.path)
        try:
            self._validate(extension)
        except BaseException:
            self.archive.close()
            raise
        self.names = set(self.archive.namelist())

    def _validate(self, extension):
        records = self.archive.infolist()
        if not records or len(records) > MAX_MEMBERS:
            raise ValueError("archive member count exceeds limit or empty")
        total = 0
        seen = set()
        for info in records:
            name = info.filename
            # ZipInfo normalizes native separators when loading a ZIP on
            # Windows. Validate the original directory entry before trusting
            # the sanitized filename; a raw backslash must remain forbidden.
            original = info.orig_filename
            if not original or "\\" in original or "\x00" in original:
                raise ValueError("unsafe raw archive path")
            if original != name:
                raise ValueError("ZIP member name normalized before validation")
            if not name or "\\" in name or name.startswith("/") or "\x00" in name:
                raise ValueError("unsafe archive path")
            segments = name.split("/")
            if any(part in (".", "..") for part in segments):
                raise ValueError("archive path traversal")
            canonical = name.lower().rstrip("/")
            if canonical in seen:
                raise ValueError("duplicate case-insensitive archive path")
            seen.add(canonical)
            if any(forbidden in "/" + canonical for forbidden in FORBIDDEN):
                raise ValueError("active/embedded Office content rejected")
            mode = (info.external_attr >> 16) & 0xFFFF
            if stat.S_IFMT(mode) == stat.S_IFLNK:
                raise ValueError("archive symlink rejected")
            if info.flag_bits & 0x1:
                raise ValueError("encrypted Office document unsupported")
            if info.file_size > MAX_MEMBER_BYTES:
                raise ValueError("oversized Office member")
            if (
                info.file_size > 100000
                and info.file_size / max(1, info.compress_size) > MAX_COMPRESSION_RATIO
            ):
                raise ValueError("suspicious compression ratio")
            total += info.file_size
            if total > MAX_TOTAL_BYTES:
                raise ValueError("oversized archive expansion")
        required = {"[Content_Types].xml", "_rels/.rels", ALLOWED[extension][1]}
        if not required.issubset(seen | {r.filename for r in records}):
            raise ValueError("missing required OOXML package members")
        if self.archive.testzip() is not None:
            raise ValueError("Office CRC integrity failure")
        for info in records:
            if not info.filename.lower().endswith(".rels"):
                continue
            rels = self.xml(info.filename)
            for rel in rels.findall("./rel:Relationship", Q):
                if (rel.get("TargetMode") or "").lower() == "external":
                    raise ValueError("external Office relationship disallowed")

    def __contains__(self, path):
        return path in self.names

    def read(self, path):
        if path not in self.archive.namelist():
            raise ValueError("missing declared Office member")
        return self.archive.read(path)

    def xml(self, path):
        data = self.read(path)
        if b"<!DOCTYPE" in data.upper() or b"<!ENTITY" in data.upper():
            raise ValueError("DTD/entity content forbidden")
        try:
            return ET.fromstring(data)
        except ET.ParseError as exc:
            raise ValueError("invalid Office XML member") from exc

    def close(self):
        self.archive.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


def _docx(pkg):
    doc = pkg.xml("word/document.xml")
    styles = pkg.xml("word/styles.xml") if "word/styles.xml" in pkg else None
    counts = Counter()
    named = []
    heading_counts = Counter()
    run_sizes = Counter()
    run_colors = Counter()
    run_fonts = Counter()
    bold_runs = italic_runs = table_count = 0
    if styles is not None:
        for item in styles.findall("./w:style", Q):
            sid = _attr(item, "w", "styleId")
            if not sid:
                continue
            name = item.find("./w:name", Q)
            base = item.find("./w:basedOn", Q)
            props = item.find("./w:rPr", Q)
            font = props.find("./w:rFonts", Q) if props is not None else None
            size = props.find("./w:sz", Q) if props is not None else None
            color = props.find("./w:color", Q) if props is not None else None
            named.append(
                {
                    "id": sid,
                    "kind": _attr(item, "w", "type"),
                    "label": _attr(name, "w", "val"),
                    "based_on": _attr(base, "w", "val"),
                    "font": _attr(font, "w", "ascii"),
                    "pt": (
                        int(_attr(size, "w", "val")) / 2
                        if _attr(size, "w", "val")
                        else None
                    ),
                    "color": _attr(color, "w", "val"),
                    "bold": bool(
                        props is not None and props.find("./w:b", Q) is not None
                    ),
                }
            )
    body = doc.find("./w:body", Q)
    if body is None:
        raise ValueError("missing DOCX body")
    for item in body:
        local = item.tag.rsplit("}", 1)[-1]
        if local == "tbl":
            table_count += 1
        if local != "p":
            continue
        props = item.find("./w:pPr/w:pStyle", Q)
        sid = _attr(props, "w", "val", "Normal")
        counts[sid] += 1
        if sid.lower().startswith("heading"):
            heading_counts[sid] += 1
        for run in item.findall("./w:r", Q):
            rpr = run.find("./w:rPr", Q)
            if rpr is None:
                continue
            if rpr.find("./w:b", Q) is not None:
                bold_runs += 1
            if rpr.find("./w:i", Q) is not None:
                italic_runs += 1
            size = rpr.find("./w:sz", Q)
            if _attr(size, "w", "val"):
                run_sizes[str(int(_attr(size, "w", "val")) / 2)] += 1
            color = rpr.find("./w:color", Q)
            if _attr(color, "w", "val"):
                run_colors[_attr(color, "w", "val")] += 1
            font = rpr.find("./w:rFonts", Q)
            if _attr(font, "w", "ascii"):
                run_fonts[_attr(font, "w", "ascii")] += 1
    sect = doc.find(".//w:sectPr", Q)
    pg = sect.find("./w:pgSz", Q) if sect is not None else None
    margin = sect.find("./w:pgMar", Q) if sect is not None else None

    def number(el, name):
        v = _attr(el, "w", name)
        return int(v) if v and re.fullmatch(r"\d+", v) else None

    return {
        "paragraph_styles": _bounded_counter(counts),
        "headings": _bounded_counter(heading_counts),
        "named_styles": sorted(named, key=lambda x: x["id"]),
        "table_count": table_count,
        "bold_run_count": bold_runs,
        "italic_run_count": italic_runs,
        "explicit_run_fonts": _bounded_counter(run_fonts),
        "explicit_run_sizes_pt": _bounded_counter(run_sizes),
        "explicit_run_colors": _bounded_counter(run_colors),
        "page_twips": {
            "width": number(pg, "w"),
            "height": number(pg, "h"),
            "left_margin": number(margin, "left"),
            "right_margin": number(margin, "right"),
        },
        "theme": _theme(pkg, "word/theme/theme1.xml"),
    }


def _xlsx(pkg):
    book = pkg.xml("xl/workbook.xml")
    root = pkg.xml("xl/styles.xml") if "xl/styles.xml" in pkg else None
    rels = (
        pkg.xml("xl/_rels/workbook.xml.rels")
        if "xl/_rels/workbook.xml.rels" in pkg
        else None
    )
    relationships = {}
    if rels is not None:
        for rel in rels.findall("./rel:Relationship", Q):
            ident, target = rel.get("Id"), rel.get("Target")
            if not ident or not target:
                raise ValueError("invalid workbook relationship")
            path = (
                posixpath.normpath(target.lstrip("/"))
                if target.startswith("/")
                else posixpath.normpath("xl/" + target)
            )
            if path.startswith("../") or path not in pkg:
                raise ValueError("unresolved workbook sheet relationship")
            relationships[ident] = path
    fonts, fills, formats, cells = [], [], [], []
    if root is not None:
        for font in root.findall("./s:fonts/s:font", Q):
            name, sz, color = (
                font.find("./s:name", Q),
                font.find("./s:sz", Q),
                font.find("./s:color", Q),
            )
            fonts.append(
                {
                    "name": name.get("val") if name is not None else None,
                    "pt": (
                        float(sz.get("val"))
                        if sz is not None and sz.get("val")
                        else None
                    ),
                    "bold": font.find("./s:b", Q) is not None,
                    "italic": font.find("./s:i", Q) is not None,
                    "color": (
                        (
                            color.get("rgb")
                            or (
                                "theme:" + color.get("theme")
                                if color.get("theme")
                                else None
                            )
                        )
                        if color is not None
                        else None
                    ),
                }
            )
        for fill in root.findall("./s:fills/s:fill", Q):
            pattern = fill.find("./s:patternFill", Q)
            color = pattern.find("./s:fgColor", Q) if pattern is not None else None
            fills.append(
                {
                    "pattern": (
                        pattern.get("patternType") if pattern is not None else None
                    ),
                    "rgb": color.get("rgb") if color is not None else None,
                }
            )
        for fmt in root.findall("./s:numFmts/s:numFmt", Q):
            formats.append({"id": fmt.get("numFmtId"), "code": fmt.get("formatCode")})
        for fmt in root.findall("./s:cellXfs/s:xf", Q):
            alignment = fmt.find("./s:alignment", Q)
            cells.append(
                {
                    "font_id": int(fmt.get("fontId", "0")),
                    "fill_id": int(fmt.get("fillId", "0")),
                    "num_fmt_id": int(fmt.get("numFmtId", "0")),
                    "border_id": int(fmt.get("borderId", "0")),
                    "horizontal": (
                        alignment.get("horizontal") if alignment is not None else None
                    ),
                    "wrap": (
                        alignment.get("wrapText") if alignment is not None else None
                    ),
                }
            )
    used = Counter()
    sheets = []
    for ordinal, sheet in enumerate(book.findall("./s:sheets/s:sheet", Q), start=1):
        rid = sheet.get(_tag("r", "id"))
        if rid not in relationships:
            raise ValueError("XLSX sheet has no resolved relationship")
        ws = pkg.xml(relationships[rid])
        count = formula_count = 0
        for cell in ws.findall(".//s:sheetData/s:row/s:c", Q):
            count += 1
            sid = cell.get("s", "0")
            if not sid.isdecimal() or int(sid) >= max(1, len(cells)):
                raise ValueError("XLSX style reference invalid")
            used[sid] += 1
            if cell.find("./s:f", Q) is not None:
                formula_count += 1
        sheets.append(
            {
                "index": ordinal,
                "cell_count": count,
                "formula_count": formula_count,
                "merged_range_count": len(ws.findall(".//s:mergeCell", Q)),
                "conditional_format_count": len(
                    ws.findall(".//s:conditionalFormatting", Q)
                ),
                "data_validation_count": len(ws.findall(".//s:dataValidation", Q)),
                "has_freeze_panes": ws.find(".//s:sheetViews/s:sheetView/s:pane", Q)
                is not None,
            }
        )
    return {
        "sheet_summaries": sheets,
        "fonts": fonts,
        "fills": fills,
        "cell_formats": cells,
        "custom_number_formats": formats,
        "used_cell_style_ids": _bounded_counter(used),
        "table_count": len(
            [x for x in pkg.names if re.fullmatch(r"xl/tables/table\d+\.xml", x)]
        ),
        "chart_count": len(
            [x for x in pkg.names if re.fullmatch(r"xl/charts/chart\d+\.xml", x)]
        ),
        "theme": _theme(pkg, "xl/theme/theme1.xml"),
    }


def _pptx(pkg):
    pres = pkg.xml("ppt/presentation.xml")
    sz = pres.find("./p:sldSz", Q)
    if sz is None or not sz.get("cx") or not sz.get("cy"):
        raise ValueError("missing PPTX slide geometry")
    width, height = int(sz.get("cx")), int(sz.get("cy"))
    if min(width, height) <= 0:
        raise ValueError("invalid PPTX slide size")
    slide_members = sorted(
        ((int(SLIDE_RE.match(n).group(1)), n) for n in pkg.names if SLIDE_RE.match(n)),
        key=lambda x: x[0],
    )
    if not slide_members:
        raise ValueError("presentation contains no slides")
    sizes, fonts, colors = Counter(), Counter(), Counter()
    shape_count = text_boxes = table_count = 0
    for ordinal, path in slide_members:
        slide = pkg.xml(path)
        for sp in slide.findall(".//p:sp", Q):
            shape_count += 1
            if sp.find("./p:txBody", Q) is not None:
                text_boxes += 1
            fill = sp.find("./p:spPr/a:solidFill", Q)
            token = _fill(fill)
            if token:
                colors[token] += 1
        table_count += len(slide.findall(".//a:tbl", Q))
        for tag in slide.findall(".//a:rPr", Q) + slide.findall(".//a:defRPr", Q):
            if tag.get("sz", "").isdecimal():
                sizes[str(int(tag.get("sz")) / 100)] += 1
            latin = tag.find("./a:latin", Q)
            if latin is not None and latin.get("typeface"):
                fonts[latin.get("typeface")] += 1
            token = _fill(tag.find("./a:solidFill", Q))
            if token:
                colors[token] += 1
    return {
        "slide_count": len(slide_members),
        "slide_indices": [n for n, _ in slide_members],
        "slide_size_emu": {"width": width, "height": height},
        "aspect_ratio": round(width / height, 6),
        "shape_count": shape_count,
        "text_box_count": text_boxes,
        "table_count": table_count,
        "chart_count": len(
            [n for n in pkg.names if re.fullmatch(r"ppt/charts/chart\d+\.xml", n)]
        ),
        "image_count": len(
            [n for n in pkg.names if n.startswith("ppt/media/") and not n.endswith("/")]
        ),
        "notes_slide_count": len(
            [
                n
                for n in pkg.names
                if re.fullmatch(r"ppt/notesSlides/notesSlide\d+\.xml", n)
            ]
        ),
        "slide_master_count": len(
            [
                n
                for n in pkg.names
                if re.fullmatch(r"ppt/slideMasters/slideMaster\d+\.xml", n)
            ]
        ),
        "explicit_font_sizes_pt": _bounded_counter(sizes),
        "explicit_fonts": _bounded_counter(fonts),
        "explicit_colors": _bounded_counter(colors),
        "theme": _theme(pkg, "ppt/theme/theme1.xml"),
    }


def analyze(file_path, source_id):
    """Return deterministic, content-minimized source/style evidence."""
    path = Path(file_path)
    if not isinstance(source_id, str) or VALID_SOURCE_ID.fullmatch(source_id) is None:
        raise ValueError("invalid source identifier")
    suffix = path.suffix.lower()
    if suffix not in ALLOWED:
        raise ValueError("unsupported Office extension")
    family = ALLOWED[suffix][0]
    with OfficePackage(path, suffix) as pkg:
        profile = {"docx": _docx, "xlsx": _xlsx, "pptx": _pptx}[family](pkg)
    return {
        "schema": SCHEMA,
        "source_id": source_id,
        "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "family": family,
        "source_type": "actual_office_package",
        "style_profile": profile,
        "style_fingerprint": _json_hash(profile),
        "extraction_quality": "STRUCTURED",
        "body_text_exported": False,
        "source_authority_transferred": False,
        "merge_authorized": False,
        "security_waiver": False,
        "rex_accepted": None,
        "binary_committed_to_public_repo": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    receipt = analyze(args.input, args.source_id)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print("STYLE_PROBE_PASS", receipt["family"], receipt["style_fingerprint"])


if __name__ == "__main__":
    main()
