"""Offline positive, negative and metamorphic OOXML style-probe tests.

All fixtures generated in an isolated temp directory. No binary fixtures,
confidential documents, or developer-local paths are committed to Git.
"""
from __future__ import annotations

import copy
import hashlib
import io
import json
from pathlib import Path
import stat
import tempfile
import unittest
import zipfile

from tools.office_style_probe import (
    ALLOWED, MAX_MEMBERS, OfficePackage, SCHEMA, analyze,
)

CT = "<Types xmlns='http://schemas.openxmlformats.org/package/2006/content-types'></Types>"
RELS = "<Relationships xmlns='http://schemas.openxmlformats.org/package/2006/relationships'></Relationships>"
THEME = """<a:theme xmlns:a='http://schemas.openxmlformats.org/drawingml/2006/main'>
  <a:themeElements><a:clrScheme name='Code Purple'><a:dk1><a:srgbClr val='17283F'/></a:dk1>
    <a:accent1><a:srgbClr val='138D88'/></a:accent1></a:clrScheme>
    <a:fontScheme name='Code Purple'><a:majorFont><a:latin typeface='Aptos Display'/></a:majorFont>
    <a:minorFont><a:latin typeface='Aptos'/></a:minorFont></a:fontScheme></a:themeElements>
  </a:theme>"""
DOCX = """<w:document xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'>
 <w:body>
  <w:p><w:pPr><w:pStyle w:val='Heading1'/></w:pPr>
  <w:r><w:rPr><w:b/><w:color w:val='216BB0'/><w:sz w:val='30'/><w:rFonts w:ascii='Aptos'/></w:rPr>
  <w:t>PRIVATE CONTENT SHOULD NEVER APPEAR IN STYLE JSON</w:t></w:r></w:p>
  <w:p><w:pPr><w:pStyle w:val='Normal'/></w:pPr>
  <w:r><w:rPr><w:i/></w:rPr><w:t>Confidential internal example</w:t></w:r></w:p>
  <w:tbl><w:tr><w:tc><w:p><w:r><w:t>Secret table cell</w:t></w:r></w:p></w:tc></w:tr></w:tbl>
  <w:sectPr><w:pgSz w:w='12240' w:h='15840'/><w:pgMar w:left='1440' w:right='1440'/></w:sectPr>
 </w:body>
 </w:document>"""
STYLES = """<w:styles xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'>
 <w:style w:type='paragraph' w:styleId='Heading1'><w:name w:val='Heading 1'/><w:basedOn w:val='Normal'/>
 <w:rPr><w:rFonts w:ascii='Aptos Display'/><w:sz w:val='32'/><w:b/><w:color w:val='216BB0'/></w:rPr></w:style>
 <w:style w:type='paragraph' w:styleId='Normal'><w:name w:val='Normal'/></w:style>
 </w:styles>"""
BOOK = """<workbook xmlns='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
 xmlns:r='http://schemas.openxmlformats.org/officeDocument/2006/relationships'>
 <sheets><sheet name='SECRET BIDDER RATE PLAN' sheetId='1' r:id='rId1'/></sheets></workbook>"""
BOOKRELS = """<Relationships xmlns='http://schemas.openxmlformats.org/package/2006/relationships'>
 <Relationship Id='rId1' Type='worksheet' Target='worksheets/sheet1.xml'/></Relationships>"""
XLSXSTYLES = """<styleSheet xmlns='http://schemas.openxmlformats.org/spreadsheetml/2006/main'>
 <numFmts count='1'><numFmt numFmtId='164' formatCode='0.0%'/></numFmts>
 <fonts count='2'><font><sz val='11'/><name val='Aptos'/></font>
  <font><b/><sz val='14'/><name val='Aptos Display'/><color rgb='FF216BB0'/></font></fonts>
 <fills count='2'><fill><patternFill patternType='none'/></fill>
 <fill><patternFill patternType='solid'><fgColor rgb='FFECF4F7'/></patternFill></fill></fills>
 <borders count='1'><border/></borders><cellXfs count='2'>
  <xf numFmtId='0' fontId='0' fillId='0' borderId='0'/>
  <xf numFmtId='164' fontId='1' fillId='1' borderId='0'><alignment horizontal='center' wrapText='1'/></xf>
 </cellXfs></styleSheet>"""
SHEET = """<worksheet xmlns='http://schemas.openxmlformats.org/spreadsheetml/2006/main'>
 <sheetViews><sheetView workbookViewId='0'><pane ySplit='2' state='frozen'/></sheetView></sheetViews>
 <sheetData><row r='1'><c r='A1' s='1' t='inlineStr'><is><t>TOP SECRET VALUE</t></is></c>
  <c r='B1'><f>SUM(C1:C2)</f><v>3</v></c></row><row r='2'><c r='C2'><v>1</v></c></row></sheetData>
 <mergeCells count='1'><mergeCell ref='D1:E1'/></mergeCells>
 <conditionalFormatting sqref='C2'><cfRule type='cellIs' priority='1'/></conditionalFormatting>
 <dataValidations count='1'><dataValidation sqref='C2' type='whole'/></dataValidations>
 </worksheet>"""
PRES = """<p:presentation xmlns:p='http://schemas.openxmlformats.org/presentationml/2006/main'>
 <p:sldSz cx='12192000' cy='6858000' type='screen16x9'/></p:presentation>"""
SLIDE = """<p:sld xmlns:p='http://schemas.openxmlformats.org/presentationml/2006/main'
 xmlns:a='http://schemas.openxmlformats.org/drawingml/2006/main'>
 <p:cSld><p:spTree><p:sp><p:spPr><a:solidFill><a:srgbClr val='138D88'/></a:solidFill></p:spPr>
 <p:txBody><a:p><a:r><a:rPr sz='2400'><a:solidFill><a:schemeClr val='accent1'/></a:solidFill>
 <a:latin typeface='Aptos Display'/></a:rPr><a:t>SECRET SPEAKER CONTENT</a:t></a:r></a:p></p:txBody>
 </p:sp></p:spTree></p:cSld></p:sld>"""


def minimal_members(kind):
    base = {"[Content_Types].xml": CT, "_rels/.rels": RELS}
    if kind == "docx":
        base.update({"word/document.xml": DOCX, "word/styles.xml": STYLES,
                     "word/theme/theme1.xml": THEME})
    elif kind == "xlsx":
        base.update({"xl/workbook.xml": BOOK, "xl/styles.xml": XLSXSTYLES,
                     "xl/_rels/workbook.xml.rels": BOOKRELS,
                     "xl/worksheets/sheet1.xml": SHEET, "xl/theme/theme1.xml": THEME,
                     "xl/charts/chart1.xml": "<chart/>", "xl/tables/table1.xml": "<table/>"})
    elif kind == "pptx":
        base.update({"ppt/presentation.xml": PRES, "ppt/slides/slide10.xml": SLIDE,
                     "ppt/slides/slide2.xml": SLIDE,
                     "ppt/theme/theme1.xml": THEME,
                     "ppt/slideMasters/slideMaster1.xml": "<p:sldMaster xmlns:p='http://schemas.openxmlformats.org/presentationml/2006/main'/>",
                     "ppt/notesSlides/notesSlide1.xml": "<p:notes xmlns:p='http://schemas.openxmlformats.org/presentationml/2006/main'/>"})
    else:
        raise ValueError(kind)
    return base


def make_archive(path, contents, *, compression=zipfile.ZIP_DEFLATED):
    with zipfile.ZipFile(path, "w", compression=compression) as archive:
        for name, payload in contents.items():
            if "\\" in name:
                # ZipInfo normalizes separators on Windows during construction.
                # Preserve intentionally malformed entries for security tests.
                member = zipfile.ZipInfo("placeholder.xml")
                member.filename = name
                member.compress_type = compression
                archive.writestr(member, payload)
            else:
                archive.writestr(name, payload)
    # On Windows, zipfile can normalize member names again at serialization,
    # even when ZipInfo.filename was explicitly set. Synthesize the precise
    # negative fixture by changing only the two name fields in the ZIP headers.
    raw = path.read_bytes()
    changed = False
    for name in contents:
        if "\\" not in name:
            continue
        with zipfile.ZipFile(path) as reader:
            if name in reader.namelist():
                continue
        normal = name.replace("\\", "/").encode("utf-8")
        unsafe = name.encode("utf-8")
        if len(normal) != len(unsafe) or raw.count(normal) != 2:
            raise AssertionError("unsafe ZIP fixture header invariant failed")
        raw = raw.replace(normal, unsafe)
        changed = True
    if changed:
        path.write_bytes(raw)
    return path


class OfficeStyleProbeProof(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.addCleanup(self.root.cleanup)
        self.workdir = Path(self.root.name)

    def make(self, kind, change=None):
        payloads = minimal_members(kind)
        if change:
            change(payloads)
        path = self.workdir / ("sample." + kind)
        return make_archive(path, payloads)

    def read(self, kind, change=None):
        return analyze(self.make(kind, change), "fixture:" + kind)

    def rejects(self, kind, change):
        with self.assertRaises(ValueError):
            self.read(kind, change)

    def test_docx_extracts_named_heading_style(self):
        x = self.read("docx")["style_profile"]
        self.assertEqual(x["headings"], {"Heading1":1})
        self.assertEqual(x["named_styles"][0]["font"], "Aptos Display")
        self.assertEqual(x["named_styles"][0]["pt"], 16)
        self.assertEqual(x["named_styles"][0]["based_on"], "Normal")

    def test_docx_tables_page_geometry_and_run_styles(self):
        x = self.read("docx")["style_profile"]
        self.assertEqual(x["table_count"], 1)
        self.assertEqual(x["page_twips"]["width"],12240)
        self.assertEqual(x["bold_run_count"],1)
        self.assertEqual(x["italic_run_count"],1)
        self.assertEqual(x["explicit_run_sizes_pt"],{"15.0":1})
        self.assertEqual(x["explicit_run_colors"],{"216BB0":1})

    def test_xlsx_style_font_fill_number_format(self):
        x = self.read("xlsx")["style_profile"]
        self.assertEqual(x["fonts"][1]["name"],"Aptos Display")
        self.assertEqual(x["fonts"][1]["color"],"FF216BB0")
        self.assertEqual(x["fills"][1]["rgb"],"FFECF4F7")
        self.assertEqual(x["custom_number_formats"][0]["code"],"0.0%")
        self.assertEqual(x["cell_formats"][1]["horizontal"],"center")
        self.assertEqual(x["used_cell_style_ids"],{"0":2,"1":1})

    def test_xlsx_formulas_charts_tables_controls(self):
        x = self.read("xlsx")["style_profile"]
        self.assertEqual(x["sheet_summaries"][0]["formula_count"],1)
        self.assertEqual(x["sheet_summaries"][0]["merged_range_count"],1)
        self.assertEqual(x["sheet_summaries"][0]["conditional_format_count"],1)
        self.assertEqual(x["sheet_summaries"][0]["data_validation_count"],1)
        self.assertTrue(x["sheet_summaries"][0]["has_freeze_panes"])
        self.assertEqual(x["chart_count"],1)
        self.assertEqual(x["table_count"],1)

    def test_pptx_numeric_slide_order_and_geometry(self):
        x = self.read("pptx")["style_profile"]
        self.assertEqual(x["slide_indices"],[2,10])
        self.assertAlmostEqual(x["aspect_ratio"],16/9,places=5)
        self.assertEqual(x["slide_count"],2)
        self.assertEqual(x["slide_master_count"],1)
        self.assertEqual(x["notes_slide_count"],1)

    def test_pptx_explicit_font_size_fill_and_shape_count(self):
        x = self.read("pptx")["style_profile"]
        self.assertEqual(x["explicit_font_sizes_pt"],{"24.0":2})
        self.assertEqual(x["explicit_fonts"],{"Aptos Display":2})
        self.assertEqual(x["explicit_colors"],{"#138D88":2,"theme:accent1":2})
        self.assertEqual(x["shape_count"],2)
        self.assertEqual(x["text_box_count"],2)

    def test_theme_scheme_font_and_color(self):
        for kind in ALLOWED.values():
            x = self.read(kind[0])["style_profile"]["theme"]
            self.assertEqual(x["colors"]["dk1"],"#17283F")
            self.assertEqual(x["fonts"]["minorFont"],"Aptos")
            self.assertEqual(x["status"],"OBSERVED")

    def test_receipt_provenance_and_gates(self):
        for kind in ALLOWED.values():
            x = self.read(kind[0])
            self.assertEqual(x["schema"],SCHEMA)
            self.assertEqual(x["family"],kind[0])
            self.assertFalse(x["body_text_exported"])
            self.assertFalse(x["source_authority_transferred"])
            self.assertFalse(x["merge_authorized"])
            self.assertFalse(x["security_waiver"])
            self.assertIsNone(x["rex_accepted"])
            self.assertEqual(len(x["source_sha256"]),64)
            self.assertEqual(len(x["style_fingerprint"]),64)

    def test_no_sensitive_body_or_sheet_name_leak(self):
        for kind in ALLOWED.values():
            data=json.dumps(self.read(kind[0]),sort_keys=True)
            for sensitive in ["PRIVATE CONTENT", "SECRET BIDDER", "SECRET SPEAKER", "Confidential internal example", "Secret table cell", "SUM(C1:C2)"]:
                self.assertNotIn(sensitive,data)
            self.assertNotIn(str(self.workdir),data)

    def test_semantic_style_hash_invariant_to_docx_text(self):
        a=self.read("docx")
        b=self.read("docx",lambda x:x.update({"word/document.xml":x["word/document.xml"].replace("PRIVATE CONTENT", "OTHER BODY CONTENT")}))
        self.assertNotEqual(a["source_sha256"],b["source_sha256"])
        self.assertEqual(a["style_fingerprint"],b["style_fingerprint"])

    def test_semantic_style_hash_invariant_to_slide_text(self):
        a=self.read("pptx")
        b=self.read("pptx",lambda x:x.update({"ppt/slides/slide10.xml":x["ppt/slides/slide10.xml"].replace("SECRET SPEAKER", "NEW SPEAKER")}))
        self.assertNotEqual(a["source_sha256"],b["source_sha256"])
        self.assertEqual(a["style_fingerprint"],b["style_fingerprint"])

    def test_deterministic_repeat_probe(self):
        path=self.make("xlsx")
        self.assertEqual(analyze(path,"fixture:xlsx"),analyze(path,"fixture:xlsx"))

    def test_style_change_modifies_fingerprint(self):
        a=self.read("pptx")
        b=self.read("pptx",lambda x:x.update({"ppt/slides/slide2.xml":x["ppt/slides/slide2.xml"].replace("sz='2400'","sz='3000'")}))
        self.assertNotEqual(a["style_fingerprint"],b["style_fingerprint"])

    def test_missing_theme_is_explicitly_absent(self):
        x=self.read("docx",lambda z:z.pop("word/theme/theme1.xml"))
        self.assertEqual(x["style_profile"]["theme"]["status"],"ABSENT")

    def test_missing_styles_is_allowed_not_invented(self):
        x=self.read("docx",lambda z:z.pop("word/styles.xml"))
        self.assertEqual(x["style_profile"]["named_styles"],[])
        self.assertEqual(x["style_profile"]["headings"],{"Heading1":1})

    def test_new_ooxml_style_changes_profile_not_authority(self):
        x=self.read("docx",lambda z:z.update({"word/styles.xml":z["word/styles.xml"].replace("Aptos Display","New Sans")}))
        self.assertEqual(x["style_profile"]["named_styles"][0]["font"],"New Sans")
        self.assertFalse(x["merge_authorized"])

    def test_no_file_rejected(self):
        with self.assertRaises(ValueError):
            analyze(self.workdir/"missing.docx","fixture:missing")

    def test_unsupported_type_rejected(self):
        p=self.workdir/"fixture.pdf"
        p.write_bytes(b"%PDF")
        with self.assertRaises(ValueError):
            analyze(p,"fixture:pdf")

    def test_renamed_archive_wrong_family_rejected(self):
        contents=minimal_members("docx")
        path=make_archive(self.workdir/"spoof.pptx",contents)
        with self.assertRaises(ValueError):
            analyze(path,"fixture:spoof")

    def test_corrupt_zip_rejected(self):
        p=self.workdir/"broken.docx"
        p.write_bytes(b"not an Office file")
        with self.assertRaises(ValueError):
            analyze(p,"fixture:broken")

    def test_invalid_source_ids_rejected(self):
        path=self.make("docx")
        for sid in ("", "../secret", "bad token", "x/../../foo", "-prefixed", "x"*97):
            with self.subTest(sid=sid),self.assertRaises(ValueError):
                analyze(path,sid)

    def test_unsafe_paths_rejected(self):
        for name in ("../steal.xml", "word/../unsafe.xml", "/abs.xml", "word\\doc.xml", "./relative.xml"):
            with self.subTest(path=name):
                path = self.make("docx", lambda x, n=name: x.update({n: "<root/>"}))
                with zipfile.ZipFile(path) as archive:
                    # The native ZIP parser may normalize filename on Windows.
                    # Assert the *original* byte-derived member identity.
                    raw_names = [entry.orig_filename for entry in archive.infolist()]
                    self.assertIn(name, raw_names)
                with self.assertRaises(ValueError):
                    analyze(path, "fixture:docx")

    def test_duplicate_case_insensitive_members_rejected(self):
        self.rejects("docx",lambda x:x.update({"WORD/DOCUMENT.XML":DOCX}))

    def test_archive_symlink_rejected(self):
        p=self.workdir/"link.docx"
        with zipfile.ZipFile(p,"w") as z:
            for name,content in minimal_members("docx").items():
                z.writestr(name,content)
            info=zipfile.ZipInfo("word/link.xml")
            info.create_system=3
            info.external_attr=(stat.S_IFLNK|0o777)<<16
            z.writestr(info,"../../exfil")
        with self.assertRaises(ValueError):
            analyze(p,"fixture:symlink")

    def test_macro_embedded_activex_and_external_links_rejected(self):
        for name in ("word/vbaProject.bin", "word/embeddings/oleObject1.bin", "ppt/activeX/activeX1.xml", "xl/externalLinks/externalLink1.xml"):
            with self.subTest(member=name):
                self.rejects("docx",lambda x,n=name:x.update({n:"malware"}))

    def test_external_relationship_rejected(self):
        rels="""<Relationships xmlns='http://schemas.openxmlformats.org/package/2006/relationships'>
        <Relationship Id='external' TargetMode='External' Target='https://example.test' Type='hyperlink'/></Relationships>"""
        self.rejects("docx",lambda x:x.update({"_rels/.rels":rels}))

    def test_invalid_xml_rejected(self):
        self.rejects("docx",lambda x:x.update({"word/document.xml":"<unclosed"}))

    def test_xml_entity_dtd_rejected(self):
        self.rejects("docx",lambda x:x.update({"word/styles.xml":"<!DOCTYPE x [<!ENTITY foo 'text'>]><x/>"}))

    def test_missing_required_members_rejected(self):
        for member in ("word/document.xml","[Content_Types].xml","_rels/.rels"):
            with self.subTest(member=member):
                self.rejects("docx",lambda x,m=member:x.pop(m))

    def test_archive_member_budget_rejected(self):
        self.rejects("docx",lambda x:x.update({f"extra/{i:04d}.xml":"x" for i in range(MAX_MEMBERS)}))

    def test_zip_bomb_ratio_rejected(self):
        self.rejects("docx",lambda x:x.update({"word/huge.xml":"z"*350000}))

    def test_xlsx_missing_sheet_link_rejected(self):
        self.rejects("xlsx",lambda x:x.update({"xl/_rels/workbook.xml.rels":RELS}))

    def test_xlsx_missing_sheet_target_rejected(self):
        self.rejects("xlsx",lambda x:x.pop("xl/worksheets/sheet1.xml"))

    def test_xlsx_traversal_sheet_target_rejected(self):
        self.rejects("xlsx",lambda x:x.update({"xl/_rels/workbook.xml.rels":BOOKRELS.replace("worksheets/sheet1.xml","../../../outside.xml")}))

    def test_xlsx_invalid_style_reference_rejected(self):
        self.rejects("xlsx",lambda x:x.update({"xl/worksheets/sheet1.xml":SHEET.replace("s='1'","s='99'")}))

    def test_xlsx_invalid_style_token_rejected(self):
        self.rejects("xlsx",lambda x:x.update({"xl/worksheets/sheet1.xml":SHEET.replace("s='1'","s='abc'")}))

    def test_xlsx_formula_never_evaluated(self):
        x=self.read("xlsx",lambda z:z.update({"xl/worksheets/sheet1.xml":SHEET.replace("SUM(C1:C2)","HYPERLINK(&quot;https://evil.test&quot;)")}))
        self.assertEqual(x["style_profile"]["sheet_summaries"][0]["formula_count"],1)
        self.assertNotIn("evil.test",json.dumps(x))

    def test_pptx_no_slides_rejected(self):
        self.rejects("pptx",lambda x:[x.pop("ppt/slides/slide2.xml"),x.pop("ppt/slides/slide10.xml")])

    def test_pptx_missing_slide_size_rejected(self):
        self.rejects("pptx",lambda x:x.update({"ppt/presentation.xml":"<p:presentation xmlns:p='http://schemas.openxmlformats.org/presentationml/2006/main'/>"}))

    def test_pptx_zero_aspect_rejected(self):
        self.rejects("pptx",lambda x:x.update({"ppt/presentation.xml":PRES.replace("cx='12192000'","cx='0'")}))

    def test_slide_shape_counter_independent_of_text(self):
        a=self.read("pptx")
        b=self.read("pptx",lambda x:x.update({"ppt/slides/slide10.xml":SLIDE.replace("SECRET SPEAKER CONTENT","other text") }))
        self.assertEqual(a["style_profile"]["shape_count"],b["style_profile"]["shape_count"])

    def test_cli_output_and_content_minimization(self):
        import subprocess,sys
        path=self.make("docx")
        output=self.workdir/"out.json"
        exe=Path(__file__).resolve().parents[1]/"tools"/"office_style_probe.py"
        r=subprocess.run([sys.executable,str(exe),str(path),"--source-id","fixture-cli","--out",str(output)],capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stderr)
        data=json.loads(output.read_text())
        self.assertEqual(data["source_sha256"],hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertFalse(data["body_text_exported"])


if __name__ == "__main__":
    unittest.main()