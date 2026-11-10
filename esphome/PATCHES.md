# Patches to ESPHome-Zehnder-RF

Upstream: https://github.com/Sanderhuisman/ESPHome-Zehnder-RF @ `7d6de29` (2023-01-26)
Local copy: `components_src/ESPHome-Zehnder-RF` (branch `esphome-2026-port`, uncommitted;
`git -C components_src/ESPHome-Zehnder-RF diff` shows the full diff).
Target: ESPHome **2026.10.2**, ESP32 Arduino framework.

No RF protocol logic (frames, addresses, channel, timing, state transitions) was changed.

## API port (needed to compile)

| File | Change | Why |
|---|---|---|
| `nrf905/__init__.py` | `class_("nRF905", fan.FanState)` → `class_("nRF905", cg.Component, spi.SPIDevice)`; dropped `fan` import | `fan.FanState` no longer exists. The nRF905 was never a fan; the C++ class is `Component` + `SPIDevice`. |
| `zehnder/fan.py` | `fan.FanState` → `cg.Component, fan.Fan` | `FanState` was renamed to `Fan` (C++ already used `fan::Fan`). |
| `zehnder/fan.py` | `fan.FAN_SCHEMA.extend({GenerateID…})` → `fan.fan_schema(ZehnderRF).extend(…)` | `FAN_SCHEMA` was removed; `fan_schema(class)` declares the ID itself. |
| `zehnder/fan.py` | `new_Pvariable` + `register_fan` → `fan.new_fan(config)` | Current idiom for fan platforms (same as the built-in template fan). |
| `zehnder/zehnder.h` | `#include ".../fan/fan_state.h"` → `#include ".../fan/fan.h"` | `fan_state.h` was removed. |

## Behaviour fix needed under the new SPI model

| File | Change | Why |
|---|---|---|
| `nrf905/nRF905.h` | setup priority `AFTER_CONNECTION` → `HARDWARE` (the `HARDWARE` line was already there, commented out) | `ZehnderRF::setup()` (priority `DATA`) writes the radio config over SPI. Since ESPHome's SPI refactor, SPI goes through a per-device delegate that only exists after `spi_setup()`. Before that, the calls hit a no-op `NULL_DELEGATE`: the writes were silently dropped and a spurious "Config write failed" was logged. If Wi-Fi was slow, the 15 s pairing timer could also start before the radio was initialised. The radio now initialises first. |

## Bug fixes in `zehnder/zehnder.cpp`

| Location | Change | Why |
|---|---|---|
| `loop()`, `case StateWaitSetSpeedConfirm` | added missing `break;` | It fell through into `default:` (harmless today, but a latent bug). |
| `rfHandleReceived()`, `StateWaitSetSpeedResponse` / `FAN_TYPE_FAN_SETTINGS` | removed duplicate `this->rfComplete();` | It was called twice in a row; idempotent, so this is cleanup. |

## Left as-is (deliberately)

- `-Wformat` warnings (`%X`/`%u` with `uint32_t`, which is `unsigned long` on Xtensa). Both are 32-bit on ESP32, so output is correct.
- Pairing still uses a random 1–254 device ID with the known 1/254 collision risk (upstream TODO).
