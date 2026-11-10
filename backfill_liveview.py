#!/usr/bin/env .venv/bin/python
"""Backfill room temperatures from the Control Box 'liveview' buffer into HA statistics.

/api/liveview/get returns the last 12 h as 193 snapshots (every 3.75 min, newest
last, no timestamps). Timing was confirmed by matching its hot-water series against
the Luxtronik boiler sensor in HA (mean error < 0.2 °C).

Only hours that end before HA's own first recorded state of each sensor are
imported (hourly mean/min/max via recorder/import_statistics), so nothing
overlaps with what the recorder compiled itself.

Usage: .venv/bin/python backfill_liveview.py [--apply]
"""
import asyncio, os, re, sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import aiohttp
from ha import HA, load_env

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "custom_components", "heatapp_rooms"))
from api import HeatappBox  # noqa: E402

load_env()
INTERVAL = timedelta(minutes=3.75)
LAST_SAMPLE_AGE = timedelta(minutes=5)  # from the alignment fit
FIELDS = {"current": "temperatuur", "desired": "doeltemperatuur"}


def slug(name):
    # some snapshots carry the raw name with a ":<n>" prefix (e.g. ":1Flo")
    return re.sub(r"^:\d+", "", name).lower().replace(" ", "_")


async def fetch_liveview():
    async with aiohttp.ClientSession() as s:
        cb = HeatappBox(s, "192.168.2.3", os.environ["CONTROLBOX_USER"],
                        os.environ["CONTROLBOX_PASS"], False)
        return (await cb.get("/api/liveview/get"))["data"]["rooms"]


async def main():
    apply = "--apply" in sys.argv
    snaps = await fetch_liveview()
    now = datetime.now(timezone.utc)
    n = len(snaps)
    series = defaultdict(list)  # entity_id -> [(ts, value)]
    for i, snap in enumerate(snaps):
        ts = now - LAST_SAMPLE_AGE - (n - 1 - i) * INTERVAL
        for key, room in snap.items():
            if not isinstance(room, dict):
                continue
            for field, suffix in FIELDS.items():
                try:
                    series[f"sensor.kamer_{slug(room['name'])}_{suffix}"].append((ts, float(room[field])))
                except (KeyError, ValueError):
                    pass

    async with HA() as h:
        for eid, pts in sorted(series.items()):
            rows = (await h.call(
                "history/history_during_period", start_time=(now - timedelta(days=2)).isoformat(),
                entity_ids=[eid], minimal_response=True, no_attributes=True)).get(eid) or []
            cutoff = (datetime.fromtimestamp(rows[0]["lu"], timezone.utc) if rows else now)
            cutoff = cutoff.replace(minute=0, second=0, microsecond=0)  # hour HA started in
            hours = defaultdict(list)
            for ts, v in pts:
                start = ts.replace(minute=0, second=0, microsecond=0)
                if start + timedelta(hours=1) <= cutoff:
                    hours[start].append(v)
            stats = [{"start": start.isoformat(), "mean": round(sum(v) / len(v), 2),
                      "min": min(v), "max": max(v)} for start, v in sorted(hours.items())]
            local = lambda iso: datetime.fromisoformat(iso).astimezone().strftime("%H:%M")
            print(f"{eid}: {len(stats)} hours before HA start {cutoff.astimezone():%H:%M} | "
                  + " ".join(f"{local(s['start'])}={s['mean']}" for s in stats))
            if apply and stats:
                await h.call("recorder/import_statistics", metadata={
                    "has_mean": True, "has_sum": False, "mean_type": 1, "name": None,
                    "source": "recorder", "statistic_id": eid, "unit_of_measurement": "°C",
                    "unit_class": "temperature"}, stats=stats)
    print("imported" if apply else "dry run (use --apply to import)")


asyncio.run(main())
