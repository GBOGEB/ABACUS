"""
splice_navigator.py -- promotes the Navigator's template-splice step from
inline Python (retyped every round, never independently reproducible) to a
saved, re-runnable script. Closes a standing gap flagged in
ENGINEERING_HANDOVER_SESSION.md / SESSION_SSOT.yaml since v12.

Usage:
    python3 splice_navigator.py <nav_data_json> <out_html> [<template_html>]

Example:
    python3 export_nav_data.py QPS_OFFER_Evaluation_FULL_v23.xlsx /tmp/nav_data_v23.json
    python3 splice_navigator.py /tmp/nav_data_v23.json QPS_RTM_BT_Navigator_v21.html
"""
import sys

def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    data_path = sys.argv[1]
    out_path = sys.argv[2]
    tpl_path = sys.argv[3] if len(sys.argv) > 3 else "navigator_template.html"

    tpl = open(tpl_path, encoding="utf-8").read()
    data = open(data_path, encoding="utf-8").read()
    if "__NAV_DATA_JSON__" not in tpl:
        raise SystemExit(f"template {tpl_path} has no __NAV_DATA_JSON__ placeholder -- wrong template file?")
    out = tpl.replace("__NAV_DATA_JSON__", data)
    open(out_path, "w", encoding="utf-8").write(out)
    print(f"wrote {out_path} ({len(out)} bytes)")

if __name__ == "__main__":
    main()
