# Scripts

All run with `.venv/bin/python` from the project root; they read `.env` via `ha.py`.

## `ha.py`
Minimal HA websocket client. `HA()` async context manager with `.call(type, **kw)` and
`.statistics(ids, start, end, period, types)`; `run(coro)` wraps `asyncio.run`. See CLAUDE.md
for the API surface.

## `kosten.py` — per-machine cost
`python kosten.py [start_iso]` (default `2025-12-01`). Pulls hourly `change`+`mean` stats for
each appliance and the tariff, multiplies each hour's energy by that hour's real price, and
prints a JSON report (per-machine kWh/cost/per_month/per_year, monthly breakdown, whole-house,
and heat-pump thermal). Heat pump has no electricity meter → only **thermal** output is metered
(`heat_amount_counter`); electricity is estimated by dividing by an assumed COP (~3.2).
Filters meter glitches to `0..cap`.

## `nacht.py` — night-shift what-if
`simulate(states)` compares washer/dryer run cost under scenarios: as-now, fixed 02:00,
cheapest night hour, cheapest hour within 24h. Used by `export.py`.

## `export.py` — datasets for the artifact dashboard
Writes `data/machines.json`, `monthly.json`, `timing.json`, `price_by_hour.json`.

## `export_automations.py` — automation datasets
Writes `data/automations.json`, `coffee_sessions.json`, `timer_options.json` (coffee auto-off
timer simulation).

## Cost findings (approx, 2026)
- Washing machine ≈ **€71/yr**, dryer ≈ **€31/yr**, coffee machine ≈ **€82/yr**.
- Night-shifting washer/dryer saves <€1/yr; midday (11–15h) ≈ €30/yr.
- Heat pump electricity ≈ **€390–510/yr** (COP 3.2 estimate; DHW ≈ half). Moving the hot-water
  reheat from 05–07h to 11–14h is ~33% cheaper per kWh ≈ **€80/yr** saved.
- Coffee auto-off (installed) expected to save ≈ €65/yr.

## `controlbox_rooms.py` — room temperatures (heatapp)

Prints per-room temperature / target / battery / status from the heatapp Gateway + Control Box,
using the browserless client in `custom_components/heatapp_rooms/api.py`. `--json` for raw data.
The same data feeds HA through the `heatapp_rooms` integration.

## `deploy_custom_component.py <name>`

Uploads `custom_components/<name>/` to HA's `/config` through the File editor add-on (ingress).
Restart HA afterwards when adding a new integration.

## `backfill_liveview.py [--apply]`

Imports the Control Box's rolling 12 h buffer (`/api/liveview/get`: 193 snapshots, every
3.75 min, newest last, no timestamps; 0.5 °C resolution) into HA as hourly mean/min/max
statistics for `sensor.kamer_*_temperatuur` / `_doeltemperatuur`, only for hours before HA's
own first recorded state. Dry run by default. Used once on 2026-10-26 (11:00–22:00).
The buffer also holds hot water (`warmwasser`), flow/return (`kessel`) and pump states (`energy`).

## DHW schedule result (analysis 2026-11-03)
Schedule changed 2026-10-09 (59 °C mornings/evenings → 50 °C 11–22h, 40 °C night). Comparing
Sep 1–Oct 8 with Oct 12–Nov 2 (vacation 20–25 Oct excluded): DHW heat **8.2 → 5.9 kWh_th/day
(−28 %)**, run time 1.10 → 0.83 h/day, share of heat made 11–15h 9 % → 64 %. Estimated
electricity (COP ≈ 3.3 from house-meter excess during DHW runs) 2.5 → 1.8 kWh/day; ≈ −34 % cost
like-for-like, ≈ €100–130/yr. Remaining expensive bits: evening reheats 18–21h (19 % of heat, inside
the 50 °C window) and morning reheats 7–8h (15 %). Scratch analysis script lived in the session scratchpad.
