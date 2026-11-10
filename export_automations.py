"""Export automation datasets for the dashboard's Automations page into ./data/."""
import asyncio
import datetime as dt
import json
from pathlib import Path

from ha import HA

OUT = Path(__file__).with_name("data")
SWITCH = "switch.koffie"
POWER = "sensor.shellyplusplugs_fcb4670d5404_power"
INSTALLED = dt.datetime(2026, 10, 8, 21, 55).astimezone()  # coffee automations went live
PRICE = 0.30  # €/kWh, recent average Zonneplan tariff incl. taxes
# Per automation: what it does in plain words, and the expected yearly saving (from the timer simulation)
INFO = {
    "koffie_auto_off": ("Coffee machine", "Turns the coffee machine off after 60 minutes on, and sends a notification with a button to turn it back on.", "timer:60"),
    "koffie_avond_uit": ("Coffee machine", "Turns the coffee machine off at 22:00 if it's still on, so it never stays on overnight.", None),
    "1767025940903": ("Kitchen", "Handles the 8-button switch in the kitchen.", None),
    "1770229695802": ("Office", "Toggles the office lights.", None),
}


def local(ts):
    return dt.datetime.fromtimestamp(ts).astimezone()


async def fetch():
    async with HA() as h:
        now = dt.datetime.now(dt.UTC)
        start = (now - dt.timedelta(days=14)).isoformat()
        states = await h.call("get_states")
        log = await h.call("logbook/get_events", start_time=start, entity_ids=[SWITCH])
        power = await h.statistics([POWER], start, period="5minute", types=["mean"])
        return states, log, power[POWER]


def sessions_from(log, power):
    pw = {r["start"] / 1000: r["mean"] for r in power if r.get("mean") is not None}
    energy = lambda a, b: sum(w * 5 / 60 for t, w in pw.items() if a <= t < b) / 1000
    out, on = [], None
    for e in log:
        if e.get("state") == "on":
            if out and e["when"] - out[-1][1] < 60:  # off/on blip within a minute: same session
                on = {"when": out.pop()[0]}
                continue
            on = e
        elif e.get("state") == "off" and on:
            out.append((on["when"], e["when"], e.get("context_name") or e.get("context_entity_id")))
            on = None
    if on:
        out.append((on["when"], dt.datetime.now().timestamp(), "still on"))
    rows = []
    for a, b, by in out:
        if b - a < 60:  # sub-minute blips (plug re-reporting state)
            continue
        rows.append({
            "start": local(a).isoformat(timespec="minutes"),
            "day": local(a).date().isoformat(),
            "minutes_on": round((b - a) / 60),
            "kwh": round(energy(a, b), 3),
            "turned_off_by": "Auto-off automation" if by and "koffie" in str(by).lower() else
                             ("Still on" if by == "still on" else "By hand or Shelly schedule"),
            "after_automation": local(a) >= INSTALLED,
        })
    return rows, energy


def timer_options(rows_raw, energy):
    """Simulated yearly saving of an auto-off after N minutes, on sessions before the automation existed."""
    before = [(a, b) for a, b in rows_raw if local(a) < INSTALLED]
    if not before:
        return []
    days = (before[-1][1] - before[0][0]) / 86400
    heat = sum(energy(a, a + 900) for a, b in before) / len(before)
    out = []
    for n in (30, 45, 60, 90, 120):
        cut = [(a, b) for a, b in before if b - a > n * 60]
        saved = sum(energy(a + n * 60, b) for a, b in cut) - 0.5 * len(cut) * heat
        out.append({"minutes": n, "kwh_per_year": round(saved / days * 365),
                    "saving_per_year_eur": round(saved / days * 365 * PRICE), "chosen": n == 60})
    return out


def main():
    states, log, power = asyncio.run(fetch())
    sess, energy = sessions_from(log, power)
    raw = [(dt.datetime.fromisoformat(r["start"]).timestamp(),
            dt.datetime.fromisoformat(r["start"]).timestamp() + r["minutes_on"] * 60) for r in sess]
    timers = timer_options(raw, energy)
    chosen = next((t["saving_per_year_eur"] for t in timers if t["chosen"]), None)

    autos = []
    for s in states:
        if not s["entity_id"].startswith("automation."):
            continue
        a = s["attributes"]
        device, what, saving = INFO.get(a.get("id"), ("", "", None))
        lt = a.get("last_triggered")
        autos.append({
            "name": a.get("friendly_name", s["entity_id"]),
            "device": device,
            "what_it_does": what,
            "status": "On" if s["state"] == "on" else "Off",
            "last_triggered": local(dt.datetime.fromisoformat(lt).timestamp()).isoformat(timespec="minutes") if lt else "Not yet",
            "saving_per_year_eur": chosen if saving == "timer:60" else None,
        })
    autos.sort(key=lambda r: (r["device"] != "Coffee machine", r["name"]))

    OUT.mkdir(exist_ok=True)
    for name, rows in [("automations", autos), ("coffee_sessions", sess), ("timer_options", timers)]:
        (OUT / f"{name}.json").write_text(json.dumps(rows, indent=1))
        print(name, len(rows), "rows")


if __name__ == "__main__":
    main()
