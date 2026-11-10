"""What-if: replay each washer/dryer run at night using the actual hourly tariffs."""
import datetime as dt
import sys
from collections import defaultdict

from ha import HA, run
from kosten import MAX_KWH_PER_HOUR, RUN_THRESHOLD, TARIFF

MACHINES = {"sensor.wasmachine_energy": "Wasmachine", "sensor.droger_energy": "Droger"}
H = 3600_000


async def fetch(start):
    async with HA() as h:
        return await h.statistics([TARIFF, *MACHINES], start, period="hour", types=["change", "mean"])


def runs_of(rows):
    s = {r["start"]: r["change"] for r in rows
         if r.get("change") is not None and 0 <= r["change"] <= MAX_KWH_PER_HOUR}
    runs, cur = [], None
    for t in sorted(s):
        if s[t] < RUN_THRESHOLD:
            continue
        if cur and t - cur[-1][0] <= H:
            cur.append((t, s[t]))
        else:
            cur = [(t, s[t])]
            runs.append(cur)
    return runs


def cost_at(profile, start, price):
    """Cost of an hourly kWh profile started at `start`; None if a price is missing."""
    total = 0.0
    for i, kwh in enumerate(profile):
        p = price.get(start + i * H)
        if p is None:
            return None
        total += kwh * p
    return total


def simulate(st):
    """Per machine: totals for actual vs shifted scenarios, plus days of price data."""
    price = {r["start"]: r["mean"] for r in st[TARIFF] if r.get("mean") is not None}
    result = {}
    for sid, name in MACHINES.items():
        tot = defaultdict(float)
        n = 0
        for r in runs_of(st[sid]):
            t0 = r[0][0]
            profile = [k for _, k in r]
            actual = sum(k * price.get(t, 0) for t, k in r)
            # the night after the run's day: start options 23:00..05:00
            day = dt.datetime.fromtimestamp(t0 / 1000).replace(hour=0, minute=0, second=0)
            night_starts = [int((day + dt.timedelta(hours=h)).timestamp() * 1000) for h in range(23, 30)]
            fixed = cost_at(profile, int((day + dt.timedelta(hours=26)).timestamp() * 1000), price)  # 02:00
            best_night = [c for c in (cost_at(profile, s, price) for s in night_starts) if c is not None]
            # best start anywhere within 24h after the actual start (upper bound, e.g. midday solar dip)
            best_any = [c for c in (cost_at(profile, t0 + i * H, price) for i in range(24)) if c is not None]
            if fixed is None or not best_night or not best_any:
                continue
            n += 1
            tot["kwh"] += sum(profile)
            tot["actual"] += actual
            tot["fixed02"] += fixed
            tot["best_night"] += min(best_night)
            tot["best_any"] += min(best_any)
        tot["runs"] = n
        result[name] = tot
    return result, len(price) / 24, price


def main(start="2026-01-01T00:00:00Z"):
    result, days, price = simulate(run(fetch(start)))
    yr = 365 / days
    for name, tot in result.items():
        n = tot["runs"]
        print(f"\n{name}: {n} runs, {tot['kwh']:.1f} kWh over {days:.0f} days")
        for k, label in [("actual", "Zoals nu"), ("fixed02", "Altijd om 02:00"),
                         ("best_night", "Goedkoopste nachtuur"), ("best_any", "Goedkoopste uur binnen 24u")]:
            save = tot["actual"] - tot[k]
            print(f"  {label:28} €{tot[k]:6.2f}  €/kWh {tot[k]/tot['kwh']:.3f}  "
                  f"besparing €{save:5.2f}  (~€{save*yr:5.2f}/jaar, {save/tot['actual']*100:4.1f}%)")

    # average price by hour of day, for context
    by_h = defaultdict(list)
    for t, p in price.items():
        by_h[dt.datetime.fromtimestamp(t / 1000).hour].append(p)
    print("\nGemiddelde prijs per uur:")
    print("  " + "  ".join(f"{h:02d}:{sum(v)/len(v):.3f}" for h, v in sorted(by_h.items())))


if __name__ == "__main__":
    main(*sys.argv[1:])
