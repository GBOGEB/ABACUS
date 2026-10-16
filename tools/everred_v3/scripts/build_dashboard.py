import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from build_bd_queue import main as regenerate_bd_queue

from control import read_history

P = pathlib.Path(__file__).resolve().parents[1]
snapshot = json.loads((P / "data/snapshot.json").read_text(encoding="utf-8"))
svgs = [
    (P / f"diagrams/{s}.svg").read_text(encoding="utf-8")
    for s in [
        "01_execution_dag",
        "02_sipoc",
        "03_causal_evidence",
        "04_preflight_gates",
        "05_native_control",
    ]
]


# Avoid accidental premature script closure when embedding JSON.
def embedded(v):
    return json.dumps(v, ensure_ascii=False).replace("</", "<\\/")


html = (P / "dashboard/template.html").read_text(encoding="utf-8")
history = read_history(P / "data/kpi_history.jsonl")
alert_path = P / "data/alerts.json"
alerts = (
    json.loads(alert_path.read_text()).get("alerts", []) if alert_path.exists() else []
)
html = html.replace("@@SNAPSHOT@@", embedded(snapshot)).replace(
    "@@SVGJSON@@", embedded(svgs)
)
html = html.replace("@@PULSES@@", embedded(history)).replace(
    "@@ALERTS@@", embedded(alerts)
)
(P / "dashboard/index.html").write_text(html, encoding="utf-8")
print("Wrote", P / "dashboard/index.html", len(html), "chars")
# Same canonical dashboard build also refreshes the read-only BD queue.
regenerate_bd_queue()
