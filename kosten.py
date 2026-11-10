"""Cost per machine: hourly kWh from HA long-term statistics x hourly Zonneplan tariff."""
import datetime as dt
import json
import sys
from collections import defaultdict

from ha import HA, run

TARIFF = "sensor.zonneplan_current_electricity_tariff"
HOUSE = "sensor.zonneplan_electricity_consumption_today"
MACHINES = {
    "sensor.wasmachine_energy": "Wasmachine",
    "sensor.droger_energy": "Droger",
    "sensor.shellyplusplugs_fcb4670d5404_energy": "Koffie",
}
CAR = "sensor.skoda_enyaq_charging_power"  # mean kW per hour == kWh in that hour
HEAT = "sensor.luxtronik_290716_0122_heat_amount_counter"
MAX_KWH_PER_HOUR = 4.0  # anything above this for a plug is a meter glitch/reset
RUN_THRESHOLD = 0.05  # kWh in an hour that counts as "running"


def ts(ms):
    return dt.datetime.fromtimestamp(ms / 1000)


async def fetch(start):
    async with HA() as h:
        return await h.statistics(
            [TARIFF, HOUSE, CAR, HEAT, *MACHINES], start, period="hour", types=["change", "mean"]
        )


def main(start="2025-12-01T00:00:00Z"):
    st = run(fetch(start))
    price = {r["start"]: r["mean"] for r in st[TARIFF] if r.get("mean") is not None}
    avg_price = sum(price.values()) / len(price)

    def hourly(sid, key="change", cap=MAX_KWH_PER_HOUR):
        out = {}
        for r in st.get(sid, []):
            v = r.get(key)
            if v is not None and 0 <= v <= cap:
                out[r["start"]] = v
        return out

    series = {name: hourly(sid) for sid, name in MACHINES.items()}
    series["Auto (laden thuis)"] = hourly(CAR, "mean", cap=12)
    house = hourly(HOUSE, cap=20)
    heat = hourly(HEAT, cap=30)

    report = {"avg_price": avg_price, "machines": {}, "monthly": defaultdict(dict)}
    for name, s in series.items():
        kwh = cost = 0.0
        months = defaultdict(lambda: [0.0, 0.0])
        runs, cur = [], None
        for t in sorted(s):
            p = price.get(t, avg_price)
            kwh += s[t]
            cost += s[t] * p
            m = ts(t).strftime("%Y-%m")
            months[m][0] += s[t]
            months[m][1] += s[t] * p
            # group consecutive "on" hours into runs
            if s[t] >= RUN_THRESHOLD:
                if cur and t - cur["end"] <= 3600_000:
                    cur["end"] = t
                    cur["kwh"] += s[t]
                    cur["cost"] += s[t] * p
                else:
                    cur = {"start": t, "end": t, "kwh": s[t], "cost": s[t] * p}
                    runs.append(cur)
        days = (max(s) - min(s)) / 86400_000 + 1 / 24 if s else 0
        report["machines"][name] = {
            "kwh": kwh, "cost": cost, "days": days,
            "eur_per_kwh": cost / kwh if kwh else 0,
            "per_month": cost / days * 30.44 if days else 0,
            "per_year": cost / days * 365 if days else 0,
            "runs": len(runs),
            "kwh_per_run": kwh / len(runs) if runs else 0,
            "cost_per_run": sum(r["cost"] for r in runs) / len(runs) if runs else 0,
            "cheapest_run": min((r["cost"] for r in runs), default=0),
            "priciest_run": max((r["cost"] for r in runs), default=0),
        }
        for m, (k, c) in months.items():
            report["monthly"][m][name] = {"kwh": k, "cost": c}

    # whole house, for context
    hk = sum(house.values())
    hc = sum(v * price.get(t, avg_price) for t, v in house.items())
    report["house"] = {"kwh": hk, "cost": hc}
    for t, v in house.items():
        m = ts(t).strftime("%Y-%m")
        d = report["monthly"][m].setdefault("Huis totaal", {"kwh": 0, "cost": 0})
        d["kwh"] += v
        d["cost"] += v * price.get(t, avg_price)
    # heat pump: only heat output is metered, estimate electricity with an assumed SCOP
    report["heat_kwh"] = sum(heat.values())
    report["heat_cost_weighted"] = sum(v * price.get(t, avg_price) for t, v in heat.items())

    json.dump(report, sys.stdout, indent=1, default=float)


if __name__ == "__main__":
    main(*sys.argv[1:])
