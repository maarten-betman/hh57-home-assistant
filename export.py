"""Export dashboard datasets (JSON row arrays) into ./data/."""
import contextlib
import datetime as dt
import io
import json
from collections import defaultdict
from pathlib import Path

import kosten
import nacht
from ha import run

OUT = Path(__file__).with_name("data")
NAMES = {"Wasmachine": "Washing machine", "Droger": "Dryer", "Koffie": "Coffee machine", "Huis totaal": "Whole house"}
r2 = lambda x: round(x, 2)

buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    kosten.main("2026-01-01T00:00:00Z")
rep = json.loads(buf.getvalue())
OUT.mkdir(exist_ok=True)
this_month = dt.date.today().strftime("%Y-%m")

machines = [
    {"machine": NAMES[k], "kwh": r2(m["kwh"]), "cost_eur": r2(m["cost"]), "per_month_eur": r2(m["per_month"]),
     "per_year_eur": r2(m["per_year"]), "eur_per_kwh": round(m["eur_per_kwh"], 3), "days_measured": round(m["days"])}
    for k, m in rep["machines"].items() if k in NAMES
]
monthly = [
    {"month": mo, "machine": NAMES[k], "kwh": r2(v["kwh"]), "cost_eur": r2(v["cost"]), "partial": mo == this_month}
    for mo, d in sorted(rep["monthly"].items()) for k, v in d.items() if k in NAMES
]

result, days, price = nacht.simulate(run(nacht.fetch("2026-01-01T00:00:00Z")))
yr = {k: 365 / m["days"] for k, m in rep["machines"].items()}
LABELS = [("actual", "As now"), ("fixed02", "Always at 02:00"),
          ("best_night", "Cheapest night hour"), ("best_any", "Cheapest hour within 24h")]
timing = [
    {"machine": NAMES[name], "scenario": label, "eur_per_kwh": round(t[k] / t["kwh"], 3),
     "per_year_eur": r2(t[k] * yr[name]), "saving_per_year_eur": r2((t["actual"] - t[k]) * yr[name])}
    for name, t in result.items() for k, label in LABELS
]
by_h = defaultdict(list)
for t, p in price.items():
    by_h[dt.datetime.fromtimestamp(t / 1000).hour].append(p)
hours = [{"hour": h, "avg_eur_per_kwh": round(sum(v) / len(v), 4)} for h, v in sorted(by_h.items())]

for name, rows in [("machines", machines), ("monthly", monthly), ("timing", timing), ("price_by_hour", hours)]:
    (OUT / f"{name}.json").write_text(json.dumps(rows, indent=1))
    print(name, len(rows), "rows")
