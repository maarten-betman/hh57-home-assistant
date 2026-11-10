# Home Assistant reference — entities, devices, network

HA at `http://homeassistant:8123` (LAN). Dutch entity names. Tariff: Zonneplan dynamic hourly.

## Energy / tariff

| Entity | Meaning |
|---|---|
| `sensor.zonneplan_current_electricity_tariff` | current price €/kWh (long-term stats: `mean`) |
| `sensor.zonneplan_current_usage` | whole-house power now (W) |
| `sensor.zonneplan_electricity_consumption_today` | house kWh today |
| `sensor.zonneplan_electricity_returned_today` | solar returned today |
| `sensor.power_production_now`, `sensor.energy_production_today` | solar |

## Appliances

| Entity | Device |
|---|---|
| `switch.koffie` | coffee machine (Shelly Plus Plug S) |
| `sensor.shellyplusplugs_fcb4670d5404_power` / `_energy` | its power / energy |
| `sensor.wasmachine_energy` | washing machine |
| `sensor.droger_energy` | dryer |
| `sensor.{wasmachine,droger}_{machine_state,job_state,completion_time,power}` | SmartThings status; end of cycle = job_state `finish` (washer) / `finished` (dryer) |
| `sensor.skoda_enyaq_charging_power` | car charging (mean kW/h ≈ kWh that hour) |

## Oven (Bosch HS836GTB6, Home Connect)

- Controlled via `home_connect.set_program_and_options`.
- `script.croissantmodus` — hot air 200 °C, 70 min, fast pre-heat. `script.oven_uit` — off.
- JSON in `automations/croissantmodus.json`, `automations/oven_uit.json`.

## Heat pump (Alpha Innotec / Novelan, Luxtronik)

- HA integration **luxtronik2**, entry "Novelan @ **192.168.2.11**:8889". Entity prefix
  `*.luxtronik_290716_0122_*`. Controller firmware V2.84.1 (LD5 230V).
- Controller web UI at **192.168.2.8** (Lux_WS on :8214). A known password gives **read-only**
  (Informatie menu only); settings are behind installer level.
- The hot-water **schedule is NOT in HA**. It's set by the **alpha home gateway at
  192.168.2.2** (an EbV *heatapp!* "controlbox"; the heat pump has `SmartHomeID/SmartHK/SmartWW=1`
  so it obeys the gateway). The gateway overrides any HA setpoint write within ~1 min, so HA
  can read but not reliably control DHW temperature. No usable HA integration for heatapp
  (sfstar/hass-heatapp_local is stale).
- Key entities: `sensor.luxtronik_290716_0122_dhw_temperature`,
  `number.luxtronik_290716_0122_dhw_target_temperature`,
  `sensor.luxtronik_290716_0122_heat_amount_heating` / `_dhw_heat_amount` (thermal counters),
  `select.luxtronik_290716_0122_thermal_desinfection_day` (set to **sunday**, 62 °C),
  `text.luxtronik_290716_0122_timer_dhw_schedule_week` (now reads `11:00-22:00/...`).
- Enabled 2026-10-09: `compressor1_impulses`, `current_heat_output`,
  `outdoor_temperature_average`, `heat_source_input_temperature`, `dhw_charging_pump`,
  `circulation_pump_heating`.

## Room heating (EbV heatapp!, custom integration `heatapp_rooms`)

- **Gateway 192.168.2.2** (radio/Z-Wave side: room sensors + floor-heating switch modules) and
  **Control Box 192.168.2.3** (room targets, schedules, status). Creds in `.env`
  (`HEATAPP_*` = gateway, `CONTROLBOX_*` = Control Box).
- Auth re-implemented in `custom_components/heatapp_rooms/api.py` (no browser):
  Control Box = challenge/response + AES-decrypted devicetoken + per-request PBKDF2-SHA512
  signature with a counter; Gateway admin = stateless, every request signed with the password.
  Read-only endpoints: gateway `/api/gateway/allmodules`, `/api/gateway/dbmodules`;
  Control Box `/api/room/list`.
- Integration installed in HA (polls every 5 min), one device per room:
  `sensor.kamer_<woonkamer|master|flo|lauren>_{temperatuur,doeltemperatuur,batterij,status}`
  + `sensor.heatapp_warm_water_doeltemperatuur`. Credentials live in the config entry.
- Deploy changes: `.venv/bin/python deploy_custom_component.py heatapp_rooms` (uploads via the
  File editor add-on's ingress API, since SSH isn't exposed), then restart HA.
- CLI: `.venv/bin/python controlbox_rooms.py [--json]`.
- Rooms → modules: Woonkamer = sensor …802 + channels 1–3 of "Module beg.grond 57"
  (00050D439719807). Master/Flo/Lauren = sensors …803/…804/…805 + channels 1/2/3 of a second
  switch module **00050D43971980F**, which the gateway has no device record for (see follow-ups).

## Lighting & Zigbee

- **Hue** bridge (in the office) runs its own Zigbee network via the `hue` integration.
- **ZHA** coordinator = *Home Assistant Connect ZBT-2*. Separate Zigbee network from Hue —
  Hue bulbs do NOT repeat for ZHA devices.
- Areas → lights:
  - **Kantoor (office):** `light.kantoor`, `light.kantoor_2`, `light.kantoor_2_2` (Hue);
    `light.awox_eglo_zm_tw` (AwoX EGLO, **ZHA** router, was weak-signal).
  - **Woonkamer:** `light.hue_ambiance_spot_3/4/5`, group `light.woonkamer`.
  - **Eettafel:** `light.hue_filament_bulb_1..4`, group `light.eettafel`.
  - **Keuken:** `light.keuken`. Downstairs group of all three = `light.beneden`.
  - **Slaapkamer (master):** two IKEA TRÅDFRI Driver 10W (PAX wardrobe), devices renamed
    *Slaapkamer kast* / *Slaapkamer kast 2*; group `light.slaapkamer`; IKEA **RODRET** remote
    bound via automation. These drivers also act as ZHA **repeaters**.
  - WiZ RGBW bulbs `light.wiz_rgbw_tunable_ab2100` / `_ab26c2` (bedroom, WiFi). Back online
    2026-11-03 after re-adding in the WiZ app (HA reconnects by MAC). `WiZ Tunable White D97D10`
    (192.168.2.20, no area) offline since 2026-10-29.
  - Wall switch **ROBB smarrt ROB_200-022-0** = Sunricher *Friends of Hue* → pair via the **Hue
    app** (Instellingen → Apparaten → +), not ZHA permit-join. Shows up via the hue integration
    as `event.works_with_hue_switch_1_button_1..4`.
- All downstairs + office Hue bulbs are **color_temp only** (tunable white, no RGB).

## Ventilation (Zehnder ComfoFan S, ESPHome RF bridge)

ESP32 + nRF905 running ESPHome 2026.10.2 (`esphome/zehnder-ventilatie.yaml`). On Wi-Fi as
`zehnder-ventilatie` / 192.168.2.45 (MAC `B0:3F:D3:51:E4:30`), native API port 6053 with encryption.
HA device **Ventilatie** (config entry `01M73N5DP364E1SXBJZNAN8BAN`, device `f3dbd0c9bc5cb68fd4254668742a001b`).

| Entity | What |
|---|---|
| `fan.ventilatie_ventilatie` | The ComfoFan. 25/50/75/100 % = speed 1–4 (fan voltage 30/50/90 %/max). Polled every 60 s; also reflects changes made with the wall remote. Paired 2026-11-10: network `0x206C9815`, main unit ID 0x59, bridge ID 0x0A. |
| `sensor.ventilatie_wifi_signaal` | Bridge Wi-Fi RSSI (dBm) |
| `button.ventilatie_hoog_10_minuten` / `button.ventilatie_hoog_30_minuten` | Boost: speed 3 for 10 / 30 minutes, then back to the previous setting |
| `button.ventilatie_herstart_ventilatie_bridge` | Reboots the ESP32 (diagnostic) |

## Dashboards

- In-HA **Mobiel** dashboard: url_path **`mobiel-dashboard`**, `sections` views:
  **Thuis, Kamers, Energie, Warmtepomp, Wassen, Automatiseringen, Huis**. When the user says "the
  dashboard for mobile", this is it — not the artifact below.
  - Kamers sections: Woonkamer, Eettafel, Keuken, Oven, Kantoor, Slaapkamer.
  - Warmtepomp view: Nu / Warm water / Kamers / Energie & kosten (incl. price charts + cost card) /
    Tellers & onderhoud.
- Shareable **claude.ai artifact** (static cost snapshot):
  https://claude.ai/artifact/QtATfbjZpPtHeWWwGXzMhw (built from `dashboard/` + `data/`).
