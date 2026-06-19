import csv
import json
from pathlib import Path

from line_s_buffer import dpdt_bar_per_min, time_to_pressure_limit_min

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / "docs" / "qps_line_s_recovery" / "generated"


def load_config():
    return json.loads((HERE / "scenarios.json").read_text())


def make_rows(config):
    rows = []
    temp = config.get("temperature_k", 300.0)
    for volume in config["volume_band_m3"]:
        for item in config["cases"]:
            net = item["m_in_g_s"] - item["m_rec_g_s"] - item.get("m_hp_g_s", 0.0)
            accumulation = max(net, 0.0)
            ribbon_rate = dpdt_bar_per_min(accumulation, volume, temp)
            energy_rate_est = ribbon_rate * (5.0 / 3.0)
            rows.append({
                "V_eff_m3": volume,
                "case": item["case"],
                "m_in_g_s": item["m_in_g_s"],
                "m_rec_g_s": item["m_rec_g_s"],
                "m_HP_g_s": item.get("m_hp_g_s", 0.0),
                "m_net_g_s": net,
                "dPdt_ribbon_bar_min": ribbon_rate,
                "dPdt_energy_est_bar_min": energy_rate_est,
                "t_plus_1bar_ribbon_min": "" if ribbon_rate <= 0 else time_to_pressure_limit_min(1.0, accumulation, volume, temp),
                "position": item["position"],
            })
    return rows


def write_outputs(rows):
    OUT.mkdir(parents=True, exist_ok=True)
    headers = list(rows[0].keys())
    with (OUT / "scenario_matrix.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
    lines = ["# Generated scenario matrix", "", "Source: models/qps_line_s/run_scenarios.py", ""]
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("|" + "|".join(["---"] * len(headers)) + "|")
    for row in rows:
        values = []
        for key in headers:
            value = row[key]
            if isinstance(value, float):
                value = f"{value:.3f}"
            values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    (OUT / "scenario_matrix.md").write_text("\n".join(lines) + "\n")


def main():
    rows = make_rows(load_config())
    write_outputs(rows)


if __name__ == "__main__":
    main()
