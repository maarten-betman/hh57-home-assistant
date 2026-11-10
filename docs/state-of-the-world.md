# State of the world — what's installed in HA

Snapshot as of 2026-10-10. Entity/device details in `docs/home-assistant.md`.

## Automations & scripts (in `automations/`, installed via REST)

- `koffie_auto_off.json` → `automation.koffie_automatisch_uit_na_60_minuten`: coffee off after
  60 min without use; power >900 W for 40 s restarts the 55-min warning timer
  (`timer.koffie_auto_uit`); warning notification has a "Nog een uur aan" button.
  (`koffie.yaml` is the superseded v1, kept for reference.)
- `koffie_avond_uit` → `automation.koffie_uit_om_22_00`: safety off at 22:00.
- `croissantmodus.json` / `oven_uit.json` → `script.croissantmodus` (hot air 200 °C, 70 min,
  fast preheat) / `script.oven_uit`.
- `warm_water_te_koud.json` → `automation.warm_water_waarschuwing_te_koud`: warns if the DHW
  tank is <33 °C for 1 h. (A `warm_water_schema` automation was tried and **removed** — the
  alpha home gateway always overrode HA's setpoint; the schedule lives in the alpha home app.)
- `slaapkamer_rodret.json` → `automation.slaapkamer_rodret_afstandsbediening`: IKEA RODRET
  remote (ieee `08:dd:eb:ff:fe:e3:95:ae`) bound to `light.slaapkamer` via `zha_event`
  (on/off = aan/uit, hold = ±25 % dim).
- `slaapkamer_schakelaar.json` → `automation.slaapkamer_wandschakelaar_robb_4_knoppen` (added
  2026-11-03): ROBB smarrt ROB_200-022-0 4-button Friends of Hue switch (paired to the **Hue
  bridge**, not ZHA; device "Slaapkamer schakelaar", `event.works_with_hue_switch_1_button_1..4`
  = TL/BL/TR/BR). Left = `light.slaapkamer` (wardrobe), right = WiZ RGB
  bulbs (`light.wiz_rgbw_tunable_ab2100`/`_ab26c2`) (swapped 2026-11-03); top = on (WiZ at fixed 2470 K, same as downstairs) / hold brighter, bottom = off / hold dimmer (±15 % per repeat).
- `automation.toggle_lichten_kantoor_2` (id 1770229695802): the office Hue switch now toggles
  **all four** office lights together (all-on if none on, else all-off), incl. the AwoX.
  Backup of the one-light original: `backups/toggle_lichten_kantoor-before.json`.

- `was_droger_klaar.json` → `automation.wasmachine_droger_klaar_melding` (added 2026-10-10):
  push when `sensor.wasmachine_job_state` → `finish` / `sensor.droger_job_state` → `finished`,
  sent only to people whose opt-in toggle is on: `input_boolean.{wasmachine,droger}_melding_{maarten,tessa}`.
  New person = add a toggle + an entry in the automation's `ontvangers` list.

Notifications target `notify.mobile_app_iphone_van_maarten` and
`notify.mobile_app_iphone_14_tessa`.

## Mobiel dashboard (`mobiel-dashboard`)

Views: Thuis, Kamers, Energie, **Warmtepomp**, **Wassen**, Automatiseringen, Huis.
- **Wassen** (added 2026-10-10): Wasmachine / Droger (status, phase, finish time while running,
  power) / notification opt-in toggles / power history + daily kWh. Backup:
  `backups/mobiel-dashboard-before-wassen.json`.
- **Warmtepomp** (added 2026-10-09): Nu / Warm water / Kamers (heatapp room temps + targets, storing-warning, 48 h graph; added 2026-10-26) / Energie & kosten (hourly price line 14d,
  daily avg price bars 30d, daily heat bars, cost-indication card) / Tellers & onderhoud.
- **Kamers → Oven** section (temperature, status, progress, croissant button, "Oven uit").
- **Kamers → Slaapkamer** section (WiZ lamp 1/2 with brightness + colour-temp sliders, group tile `light.slaapkamer` + Kast 1/Kast 2). Backup `backups/mobiel-dashboard-before-slaapkamer-wiz.json`.
- Croissant buttons use an emoji SVG picture card (no `mdi:croissant`).
- **Thuis → Ventilatie** section (ComfoFan tile with speed selector, "Hoog 10 min" / "Hoog 30 min"
  boost tiles). Backup `backups/mobiel-dashboard-before-ventilatie.json`.

Pre-edit backups are in `backups/mobiel-dashboard-before-*.json`.

## Heat pump / hot water

- DHW schedule is in the **alpha home app**: 50 °C 11:00–22:00, 40 °C overnight (confirmed; HA
  reads it in `text...timer_dhw_schedule_week`). HA cannot reliably set it (gateway overrides).
- Weekly thermal disinfection enabled: **Sunday, 62 °C**
  (`select...thermal_desinfection_day = sunday`).

## Room heating sensors

- `heatapp_rooms` custom integration installed 2026-10-26 (see `docs/home-assistant.md`).
- Bedrooms (Master, Flo, Lauren) show status **problem**: their floor-heating switch module
  00050D43971980F is missing from the gateway (channels status 2). Room sensors themselves are
  fine (battery 100 %, reporting). Master & Lauren are also pinned min = max = 14 °C.

## Lighting / Zigbee fix (office AwoX)

- Problem: `light.awox_eglo_zm_tw` (AwoX EGLO, ZHA) had a dying link (LQI 8, RSSI −98) — no
  repeater near it; the in-room Hue bridge is a *separate* Zigbee network and can't help.
- Fix: added **two IKEA TRÅDFRI Driver 10W** (master-bedroom PAX) to ZHA as routers/repeaters.
  After power-cycling the AwoX it rose to LQI ~48 and passed a 6/6 command test.
- To re-pair IKEA remotes: ZHA permit-join (`zha/permit` or the Settings UI) + a `zha_event`
  automation. **Do NOT use Touchlink** ("hold remote near lamp") — it can pull a driver off ZHA.

## Open follow-ups / offers

- **Zehnder ComfoFan S RF bridge** (ESP32 + nRF905, ESPHome 2026.10.2, locally ported component):
  **working since 2026-11-10.** Paired with the fan, in HA as device **Ventilatie**
  (`fan.ventilatie_ventilatie`, 25/50/75/100 % = speed 1–4; `sensor.ventilatie_wifi_signaal`;
  `button.ventilatie_herstart_ventilatie_bridge`). Speeds 1–3 verified from HA. Boost buttons
  `button.ventilatie_hoog_10_minuten` / `_30_minuten`. Board is on Wi-Fi at 192.168.2.45. Open:
  permanent placement (desk is at the edge of RF range; don't power it from the fan's circuit).
  Runbook: `esphome/README.md`.

- Re-measure the AwoX link after the antenna move settled (may improve if it routes via a driver).
- `Slaapkamer kast 2` driver has a weak link to the coordinator itself (LQI 8) — reposition or
  power-cycle if it acts flaky.
- Email draft to the installer to get the alpha home gateway admin password / disable SmartWW so
  HA could control DHW directly (and smart, price/solar-aware heating).
- Optional `script.lichtshow_beneden` (a reusable downstairs light show) — not yet saved.
- Camera: the Mi 360° 1080p (MJSXJ02CM) has no clean local stream; a native-RTSP camera
  (Reolink/Tapo) is the easy path. See chat history.
- Bedroom floor-heating switch module (00050D43971980F) missing from the heatapp gateway:
  check power/LEDs upstairs; re-include via gateway → Radio Components, or ask the installer.
