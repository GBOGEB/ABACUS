"""Canonical MINERVA CryoCell line database (v5).

Single source of truth for the revised colour scheme + line nomenclature.
Extracted/derived from:
  - PID Nomenclature MINERVA CryoCell (QCELL-LB).xlsx  (valve box-jumper, cryomodule)
  - QCELL - Auxilliary lines (NA.CP).xlsx  (Table: U/W/S/V interfaces, WPS)
  - User design brief (cryogenic colour scheme + flow rates)

Consumed by build_pid_v5.py and build_line_spec_master.py so the drawing,
the spec table and the Excel master never drift apart.
"""

# ---------------------------------------------------------------------------
# Revised colour palette (cryogenic focus) - user brief Phase 2
# ---------------------------------------------------------------------------
# group:  cold | thermal | warm | scope
LINES = [
    # key   desig  group     main_color  branch_color name                       temp        press     flow       size    moc     desc
    ("A",   "A",   "cold",   "#0000FF",  "#000080",  "4.5 K primary He",         "4.5 K",    "3 bar",  "~50 g/s", "DN50", "SS316L", "Main 4.5 K helium circuit"),
    ("Ap",  "A'",  "cold",   "#000080",  "#000080",  "4.5 K branches",           "4.5 K",    "3 bar",  "varies",  "DN25", "SS316L", "Branches from Line A"),
    ("B",   "B",   "cold",   "#00FFFF",  "#008B8B",  "2 K primary He",           "2 K",      "27 mbar","~47.5 g/s","DN40", "SS316L", "Main 2 K helium circuit"),
    ("Bp",  "B'",  "cold",   "#008B8B",  "#008B8B",  "2 K branches",             "2 K",      "27 mbar","varies",  "DN25", "SS316L", "Branches from Line B"),
    ("D",   "D",   "thermal","#FF8000",  "#FFB366",  "40 K shield inlet",        "40 K",     "14 bar", "TBD",     "DN32", "CU",     "Thermal shield inlet (40 K)"),
    ("Dp",  "D'",  "thermal","#FFB366",  "#FFB366",  "40 K branches",            "40 K",     "14 bar", "varies",  "DN20", "CU",     "Branches from Line D"),
    ("E",   "E",   "thermal","#FF0000",  "#CC0000",  "60 K shield outlet",       "60 K",     "13 bar", "TBD",     "DN32", "CU",     "Thermal shield outlet (60 K, ~20 K rise)"),
    ("Ep",  "E'",  "thermal","#CC0000",  "#CC0000",  "60 K branches",            "60 K",     "13 bar", "varies",  "DN20", "CU",     "Branches from Line E"),
    ("W",   "W",   "warm",   "#00FF00",  "#BFFF00",  "WPS warm return",          "4.5 K-300 K","6 bar","~2.5 g/s","DN20", "SS304",  "Warm return to QRB (cold->warm gradient)"),
    ("S",   "S",   "warm",   "#BFFF00",  "#BFFF00",  "WPS service / safety",     "2-292 K",  "1.05 bar","TBD",    "DN15", "SS304",  "WPS service line (S interface)"),
    ("U",   "U",   "warm",   "#808000",  "#808000",  "WPS GHe supply inlet",     "292 K",    "14 bar", "TBD",     "DN15", "SS304",  "WPS supply inlet only (U interface)"),
    ("OUT", "OS",  "scope",  "#808080",  "#808080",  "Outside scope",            "-",        "-",      "-",       "-",    "-",      "Outside battery-limit / reference"),
]

# fast lookup by key
LINE_BY_KEY = {l[0]: l for l in LINES}

# Mapping from extracted SVG stroke-colour classes (svg_extract CLASS_COLORS)
# to the v5 line keys.  The geometry only distinguishes a handful of classes;
# primary vs branch is resolved by run-length in build_pid_v5.
#   svg class  ->  v5 main key (primary), branch key
CLASS_TO_LINE = {
    "A":     ("A", "Ap"),
    "B":     ("B", "Bp"),
    "D":     ("D", "Dp"),
    "E":     ("E", "Ep"),
    "WATER": ("W", "S"),     # green geometry => warm return W (branch styled as S/lime)
    "AIR":   ("OUT", "OUT"),  # instrument air not in cryo scope -> outside/grey
    "QINFRA":("OUT", "OUT"),
}

# column order for the master spec table
SPEC_COLUMNS = ["Line", "Group", "Colour", "Temp", "Pressure", "Flow",
                "Size (DN)", "MOC", "Description"]


def spec_rows():
    """Rows for the LINE SPECIFICATION TABLE (drawing + xlsx)."""
    grp_name = {"cold": "COLD (cold header)", "thermal": "THERMAL SHIELD",
                "warm": "WARM (WPS)", "scope": "REFERENCE"}
    rows = []
    for key, desig, group, mc, bc, name, temp, press, flow, size, moc, desc in LINES:
        rows.append({
            "key": key, "Line": desig, "Group": grp_name[group],
            "group": group, "Colour": mc, "branch_colour": bc,
            "name": name, "Temp": temp, "Pressure": press, "Flow": flow,
            "Size (DN)": size, "MOC": moc, "Description": desc,
        })
    return rows
