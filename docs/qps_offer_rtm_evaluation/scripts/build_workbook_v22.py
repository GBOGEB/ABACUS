"""
build_workbook_v22.py -- fixes a real chart data-range bug GBO spotted from a
screenshot of the "Average Weighted S by Domain" chart (DASHBOARD_2, chart C):
Series 1 looked incomplete/incoherent against the x-axis category labels.

Root cause (confirmed directly against the saved workbook, not guessed from
the screenshot): DOMAIN_SUMMARY's real per-domain table is rows 6-27 (22
domains, matching the 22 rows export_nav_data.py's domainSummary array has
always had). The chart built in build_workbook_v19.py referenced
min_row=5/6, max_row=41 for both the data (col G, Average Weighted S) and
category (col A, Domain name) series. Rows 29-41 are NOT part of the domain
table -- they're a second, unrelated "Cluster breakdown (C1-C8)" table lower
on the same sheet (its own header/notes start at row 29, cluster labels
C1..C8 + "Not linked" run 33-41, with NO value in column G for any of them).
So the chart was pulling 15 extra category ticks (row 28 blank + rows 29-41)
with no matching numeric value -- exactly "series incomplete/incoherent with
x-axis category tiles."

Fix: trim both References to max_row=27 (the real end of the domain table).
Also widened the chart height slightly now that it's 22 real bars instead of
36 padded ones, so bars aren't overly thin.

IN:  QPS_OFFER_Evaluation_FULL_v21.xlsx
OUT: QPS_OFFER_Evaluation_FULL_v22.xlsx
"""
import warnings
warnings.filterwarnings("ignore")
import openpyxl
from openpyxl.chart import BarChart, Reference

IN = "QPS_OFFER_Evaluation_FULL_v21.xlsx"
OUT = "QPS_OFFER_Evaluation_FULL_v22.xlsx"

wb = openpyxl.load_workbook(IN, data_only=False)
d2 = wb["DASHBOARD_2"]

# Locate and remove the existing (buggy) chart C by its title, then re-add a
# corrected one in the same anchor position -- openpyxl has no in-place chart
# edit, so replace it.
anchor = "A52"
remaining = []
removed = 0
for ch in d2._charts:
    title_text = None
    try:
        if ch.title and ch.title.tx and ch.title.tx.rich:
            for p in ch.title.tx.rich.p:
                for r in (p.r or []):
                    if r.t:
                        title_text = r.t
    except Exception:
        pass
    if title_text == "Average Weighted S by Domain":
        removed += 1
        continue
    remaining.append(ch)
d2._charts = remaining
assert removed == 1, f"expected to remove exactly 1 old chart, removed {removed}"

chC = BarChart()
chC.type = "bar"
chC.title = "Average Weighted S by Domain"
chC.y_axis.title = "Domain"
dataC = Reference(wb["DOMAIN_SUMMARY"], min_col=7, min_row=5, max_row=27)   # G, header row 5 + 22 real domains
catsC = Reference(wb["DOMAIN_SUMMARY"], min_col=1, min_row=6, max_row=27)
chC.add_data(dataC, titles_from_data=True)
chC.set_categories(catsC)
chC.height, chC.width = 14, 15
d2.add_chart(chC, anchor)

wb.save(OUT)
print(f"wrote {OUT}")
print("chart C 'Average Weighted S by Domain' rebuilt: data/category range now rows 6-27 (22 real domains, was 6-41)")
