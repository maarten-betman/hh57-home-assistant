# energie-kosten — Home Assistant energy & home automation

Personal project for querying a home **Home Assistant** (HA) instance on the LAN:
analysing what appliances cost to run on a dynamic electricity tariff, and
installing/maintaining HA automations, dashboards and devices.

Owner: Maarten (mbetman@hotmail.com). Language of HA entities/dashboards: **Dutch**.
Tariff: **Zonneplan** dynamic hourly electricity.

## Connecting to Home Assistant

- Config is in **`.env`** (chmod 600, git-ignored): `HA_TOKEN` (long-lived token) and
  `HA_URL=http://homeassistant:8123`. If `.env` is missing, ask the user to recreate it;
  the token was once pasted in chat — advise rotating it if that happens again.
- The **claude.ai Home Assistant MCP connector returns 502** and is unreliable. Do **not**
  depend on it. Talk to HA directly instead:
  - **Websocket** via `ha.py` (`from ha import HA`) for states, statistics, history, logbook,
    lovelace config, ZHA, registries.
  - **REST** via `curl` for calling services and driving config-entry flows (these don't work
    cleanly over our minimal websocket client).
- The `.venv` has `websockets` installed. Run scripts with `.venv/bin/python`.

### ha.py quick reference

```python
from ha import HA, run
async def main():
    async with HA() as h:
        states = await h.call("get_states")
        await h.call("call_service", domain="light", service="turn_on",
                     service_data={...}, target={"entity_id": "light.x"})
        stats = await h.statistics([ "sensor.x" ], start_iso, end_iso,
                                   period="hour", types=["change","mean"])
run(main())
```

`h.call(type, **kw)` sends a websocket command and returns `result`. Useful types:
`get_states`, `recorder/statistics_during_period`, `history/history_during_period`,
`logbook/get_events`, `lovelace/config` (+`/config/save`), `zha/devices`, `zha/permit`,
`config/entity_registry/list`, `config/device_registry/list|update`,
`config/area_registry/list`, `config_entries/get`.

### REST patterns (curl)

```bash
set -a; . ./.env; set +a
# call a service
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" \
  -d '{"entity_id":"light.x"}' "$HA_URL/api/services/light/turn_on"
# install/replace an automation (id in the URL)
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" \
  --data @automations/foo.json "$HA_URL/api/config/automation/config/foo_id"
# validate a Jinja template
curl -s -X POST -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" \
  -d '{"template":"{{ states(\"sensor.x\") }}"}' "$HA_URL/api/template"
```
Config-entry flows (e.g. creating a Group helper) are REST too — see `docs/lighting.md`.

## Conventions / rules

- **Always back up the Lovelace config before editing it.** Save a copy under `backups/`
  (e.g. `mobiel-dashboard-before-<change>.json`) via `lovelace/config` before
  `lovelace/config/save`.
- **Never test-run anything that switches a real appliance** (washer, dryer, oven, coffee).
  Lights are fine to toggle when troubleshooting, but restore their prior state.
- **`mdi:croissant` does not exist** (404 in MDI). The croissant buttons use a `picture`
  card with an inline emoji SVG data URI.
- **Meter glitches:** some cumulative counters log negative/huge jumps. When summing hourly
  `change`, filter to `0 <= change <= cap` (coffee/heat counters do this).
- Secrets: don't commit `.env`; don't echo the token into logs.

## Layout

- `ha.py` — websocket client (the one dependency for the Python scripts).
- `kosten.py`, `nacht.py`, `export.py`, `export_automations.py` — cost analysis + dataset
  export. See `docs/scripts.md`.
- `automations/` — JSON/YAML of HA automations & scripts we authored (source of truth we keep).
- `backups/` — pre-edit snapshots of the Lovelace dashboard and automations.
- `dashboard/` — the shareable **claude.ai artifact** dashboard (static snapshot), separate
  from the in-HA Mobiel dashboard.
- `data/` — exported JSON datasets feeding the artifact dashboard.
- `esphome/` — ESPHome config for the **Zehnder ComfoFan S RF bridge** (ESP32 + nRF905), with its
  own venv and a locally ported external component. **Runbook + current status:
  `esphome/README.md`** (in progress: compiled, not yet flashed/paired).

## Docs

- `docs/home-assistant.md` — key entity IDs, devices, network addresses.
- `docs/scripts.md` — what each Python script does and how to run it.
- `docs/state-of-the-world.md` — what's currently installed in HA (automations, dashboard
  views, lighting/Zigbee, heat pump) and the open follow-ups.

There is also a persistent memory file at
`~/.claude/projects/-home-betman-project-personal-energie-kosten/memory/home-assistant-setup.md`
with the same facts in condensed form.
