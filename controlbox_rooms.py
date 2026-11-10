#!/usr/bin/env .venv/bin/python
"""Print room temperatures from the heatapp Gateway + Control Box (read-only).

Uses the same browserless client as the HA integration
(custom_components/heatapp_rooms/api.py), which runs in HA and polls every 5 min.

Usage: .venv/bin/python controlbox_rooms.py [--json]
"""
import asyncio, json, os, sys
import aiohttp
from ha import load_env

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "custom_components", "heatapp_rooms"))
from api import HeatappBox, fetch_rooms  # noqa: E402

load_env()


async def main():
    async with aiohttp.ClientSession() as s:
        gw = HeatappBox(s, "192.168.2.2", os.environ["HEATAPP_USER"], os.environ["HEATAPP_PASS"], True)
        cb = HeatappBox(s, "192.168.2.3", os.environ["CONTROLBOX_USER"], os.environ["CONTROLBOX_PASS"], False)
        data = await fetch_rooms(gw, cb)
    if "--json" in sys.argv:
        print(json.dumps(data, indent=1))
        return
    print(f"{'room':11}{'temp':>6}{'target':>8}{'day':>6}{'night':>7}{'batt':>6}{'seen':>6}  status")
    for r in data["rooms"].values():
        missing = r["missing_actuators"]
        print(f"{r['name']:11}{r['temperature']!s:>6}{r['target']!s:>8}{r['target_day']!s:>6}"
              f"{r['target_night']!s:>7}{r['battery']!s:>5}%{r['last_seen_min']!s:>4}m  "
              f"{r['status']}{'  missing: ' + ','.join(missing) if missing else ''}")


asyncio.run(main())
