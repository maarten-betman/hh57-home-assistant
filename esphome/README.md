# Zehnder ComfoFan S: ESPHome RF bridge (ESP32 + nRF905)

Makes an ESP32 act as a Zehnder RFZ remote over an nRF905 radio (868 MHz, channel 118), so
Home Assistant can control the ComfoFan S R. It uses the external component
`Sanderhuisman/ESPHome-Zehnder-RF`, ported locally to ESPHome 2026.x.

## Status (2026-11-10)

| Step | State |
|---|---|
| 1. Project, venv, secrets | ✅ done (ESPHome **2026.10.2**) |
| 2. Compile | ✅ compiles. Upstream fails (`fan.FanState` removed); the local port works. See `PATCHES.md`. |
| 3. Port component + bug fixes | ✅ done; diff in `patches/zehnder-rf-esphome-2026.patch` |
| 4. Flash over USB | ⏳ **not done**. The first laptop runs WSL2 with no admin rights, so usbipd-win can't be installed to pass the USB port through. |
| 5. Pairing with the fan | ⏳ not done |
| 6. Add to Home Assistant | ⏳ not done |

Wi-Fi credentials are still `CHANGE_ME` placeholders on purpose. See step 2 for the two options.

## Files

| Path | What |
|---|---|
| `zehnder-ventilatie.yaml` | The device config. Logger is **temporarily VERBOSE** for pairing (see step 8). |
| `secrets.yaml` | **git-ignored, private.** Wi-Fi, API encryption key, OTA and AP passwords. |
| `secrets.example.yaml` | The keys `secrets.yaml` must contain. |
| `make_secrets.py` | Creates or completes `secrets.yaml` with random keys. Never overwrites, never prints values. |
| `requirements.txt` | `esphome==2026.10.2` (pinned: the port was built and tested against this version). |
| `components_src/ESPHome-Zehnder-RF/` | Upstream clone @ `7d6de29` with the port applied (uncommitted, branch `esphome-2026-port`). |
| `patches/zehnder-rf-esphome-2026.patch` | The same changes as a patch, so `components_src` can be rebuilt from upstream. |
| `PATCHES.md` | What was changed in the component, and why. |
| `.venv/`, `.esphome/` | Machine-specific (venv, build cache). **Don't copy them.** Recreate them. |

## Hardware

- Otronic ESP32 USB-C WROOM 4MB DevKit V1 (30-pin, Dxx = GPIOxx). USB chip: **CH340**
  (VID 1A86 / PID 7523, verified on the first laptop, where it shows up as `USB-SERIAL CH340 (COM3)`).
- NRF905SE module with SMA antenna. **Use an 868 MHz antenna, not 433 MHz.**

| nRF905 | ESP32 | | nRF905 | ESP32 |
|---|---|---|---|---|
| VCC | 3V3 (never 5V) | | CSN | GPIO23 (D23) |
| GND | GND | | CD | GPIO33 (D33) |
| SCK | GPIO14 (D14) | | CE | GPIO27 (D27) |
| MOSI | GPIO13 (D13) | | PWR | GPIO26 (D26) |
| MISO | GPIO12 (D12) ⚠ strapping pin | | TXEN | GPIO25 (D25) |
| AM, DR, CLK | not connected | | | |

---

## 0. Move to the other laptop

1. Copy the whole `esphome/` folder **except** `.venv/` and `.esphome/`.
2. **Treat `secrets.yaml` as a password file.** Move it privately (USB stick, password manager),
   not by email, chat or git. Nothing has been flashed yet, so if it gets lost, just run
   `python3 make_secrets.py` to generate new keys.
3. If `components_src/` didn't come along, rebuild it from upstream:
   ```bash
   git clone https://github.com/Sanderhuisman/ESPHome-Zehnder-RF components_src/ESPHome-Zehnder-RF
   git -C components_src/ESPHome-Zehnder-RF checkout 7d6de29
   git -C components_src/ESPHome-Zehnder-RF apply ../../patches/zehnder-rf-esphome-2026.patch
   ```

## 1. Install ESPHome (in a venv, not globally)

Linux / macOS:
```bash
cd esphome
uv venv .venv --python 3.12 && uv pip install --python .venv/bin/python -r requirements.txt
# without uv:  python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/esphome version        # -> Version: 2026.10.2
```
Windows (PowerShell, no admin needed):
```powershell
cd esphome
py -3.12 -m venv .venv ; .venv\Scripts\pip install -r requirements.txt
.venv\Scripts\esphome version
```
On Windows, use `.venv\Scripts\esphome` wherever this file says `.venv/bin/esphome`. If the build
fails with path-length errors, move the folder to a short path such as `C:\esphome`.

Don't upgrade ESPHome casually. The component had to be ported once already. If you do upgrade,
recompile first and check for errors before flashing.

## 2. Secrets and Wi-Fi

`python3 make_secrets.py` fills in any missing keys (API key, OTA password, AP password). For
Wi-Fi, pick one of these:

- **A. Put the credentials in the file:** edit `wifi_ssid` / `wifi_password` in `secrets.yaml`
  yourself. Use a 2.4 GHz network only. The compiled firmware in `.esphome/build/` will then contain
  the password in plain text. It's git-ignored, but keep it local.
- **B. Use the fallback hotspot:** keep the placeholders and flash. When Wi-Fi fails, the ESP32
  opens a hotspot called `zehnder-ventilatie fallback`. Join it with your phone, and on the page
  that opens (or `http://192.168.4.1`) choose your network and type the password. It's stored only
  on the ESP32.
  **Before using B, password-protect the hotspot.** The captive portal also allows web firmware
  upload, so an open hotspot lets anyone nearby flash the device. Add this to the YAML:
  ```yaml
  wifi:
    ap:
      ssid: "${name} fallback"
      password: !secret ap_password     # already generated in secrets.yaml
  ```

## 3. Compile

```bash
.venv/bin/esphome compile zehnder-ventilatie.yaml
```
Expected result: `INFO Successfully compiled program.` (about 50 % flash, 26 % RAM). Two kinds of
warnings are known and harmless:
- `WARNING GPIO12 is a strapping pin…`
- `-Wformat` warnings in `nRF905.cpp` / `zehnder.cpp` (`%X` with `uint32_t`)

## 4. Flash over USB

Find the serial port:

| OS | Port | Driver |
|---|---|---|
| Linux | `/dev/ttyUSB0` (`ls /dev/ttyUSB*`) | `ch341` in the kernel. Your user must be in the `dialout` group. |
| macOS | `/dev/cu.usbserial-*` or `/dev/cu.wchusbserial*` (`ls /dev/cu.*`) | Built into recent macOS. Otherwise install WCH's **CH34x** driver. |
| Windows | `COMx`: Device Manager → Ports | Usually installs automatically. Otherwise install WCH's **CH341SER** driver. |
| WSL2 | `/dev/ttyUSB0` after passthrough | Needs **usbipd-win** (one-time admin): `winget install --exact dorssel.usbipd-win`, then `usbipd list`, `usbipd bind --busid <BUSID>`, `usbipd attach --wsl --busid <BUSID>` |

Then run:
```bash
.venv/bin/esphome run zehnder-ventilatie.yaml --device /dev/ttyUSB0     # or COM3, /dev/cu.…
```
`esphome run` compiles, uploads, and then streams the serial log. Keep that log open for steps 5–6.

- **Upload stuck at `Connecting…`:** hold the **BOOT** button until `Writing at 0x…` appears.
- **Board won't boot or flash reliably with the nRF905 attached:** the likely cause is GPIO12, a
  strapping pin that sets flash voltage at boot. To confirm, pull the MISO wire and try again. If
  that helps, move MISO from **D12 to D19** and change the YAML to `miso_pin: GPIO19`, then
  recompile and flash.

**No admin rights at all?** Flash from Chrome or Edge at <https://web.esphome.io> → *Connect* →
pick the CH340 port → *Install* → choose `.esphome/build/zehnder-ventilatie/build/firmware.factory.bin`.
Web Serial needs no admin, only the CH340 driver. Its *Logs* view shows the serial output.

## 5. Check that the nRF905 initialises

Right after boot, the log should show roughly this:
```
[D][nRF905]: Start nRF905 init
[V][nRF905]: Config:  Channel 118 Band 868 MHz -> 868400000 … CRC On -> 16  TX Power 10 dBm
[V][nRF905]: Write config OK
[D][nRF905]: Set TX Address: 0x89816EA9
[D][nRF905]: nRF905 Setup complete
```
`Write config OK` means the radio's registers read back exactly what was written, so SPI works.
You'll see it more than once, because the Zehnder component reconfigures the radio too.

**`[E][nRF905]: Config write failed`** means the SPI link is broken. Check SCK/MOSI/MISO/CSN, that
VCC is on 3V3, and that GND is shared.

## 6. Pair with the ComfoFan

How it works: 15 s after boot, if no pairing is stored, the ESP picks a random remote ID and
broadcasts a join request on link address `0xA55A5AA5`. It retries 10× with 1 s timeouts, then
starts over with a new ID. It keeps looping until the fan answers.

1. With the ESP running and the log open, wait for `Invalid config, start paring` (sic) followed by
   repeating `Start discovery with ID …` / `No data received, retry again (left: …)` lines.
2. **Put the fan in pairing mode:** cut the ComfoFan's power briefly and switch it back on, the same
   way you'd pair an RFZ remote. The fan only accepts new remotes for a limited time after power-up.
3. Restart the ESP32 right away (EN button, or the *Herstart ventilatie-bridge* button). Discovery
   then starts 15 s later, inside the fan's window. If the ESP was already looping discovery, it may
   pair without the restart.
4. **Success** looks like this:
   ```
   Discovery: Found unit type 0x01 (Main) with ID 0x.. on network 0x........
   Discovery: Link successful to unit with ID 0x.. on network 0x........
   Discovery: received network join success 0x0D
   Saving pairing config
   ...
   Query device
   Received fan settings; speed: 0x02 voltage: 50 timer: 0
   ```
   After a reboot you should see `Config load ok` and then `Config data valid, start polling`.

**If pairing doesn't work:**

| What the log shows | Likely cause | Try |
|---|---|---|
| Only retry/timeout loops; never `Addr match`, `Rx Invalid` or `Found unit` | The fan isn't answering: pairing window missed, out of range, or the wrong band | Power-cycle the fan again and restart the ESP. Pair within a few metres of the fan, with the antenna screwed on. Check the antenna is for 868 MHz, not 433 MHz. Check the fan actually has the RF receiver. |
| `Rx Invalid` / `Addr match` but no `Found unit` | Something is being received but fails CRC: weak signal, or a frequency offset | Move closer. The code assumes a **16 MHz** crystal on the nRF905; check the marking on the module's crystal. |
| `Found unit …` then `Query Timeout` and back to discovery, or `Received unknown link success …` | Handshake incomplete; if it keeps happening, possibly an ID collision | Retry a few times. If it persists, erase flash (below) and pair again with a fresh ID. |
| `Airway too busy, giving up` | The CD (carrier detect) pin is stuck high | Check the CD wire (D33), and look for constant 868 MHz interference. |
| `Config write failed` | SPI wiring | See step 5. |

To erase flash, which clears the stored pairing (and any Wi-Fi entered via the hotspot):
```bash
.venv/bin/esptool --port /dev/ttyUSB0 erase-flash      # esptool v5 syntax (v4: esptool.py erase_flash)
.venv/bin/esphome run zehnder-ventilatie.yaml --device /dev/ttyUSB0
```

## 7. Add to Home Assistant and test the fan

1. Once the ESP is on Wi-Fi, HA should discover it: **Settings → Devices & services → Discovered:
   zehnder-ventilatie → Configure**. When asked, paste `api_encryption_key` from `secrets.yaml`.
   If it isn't discovered, use *Add integration → ESPHome* with host `zehnder-ventilatie.local`
   (or its IP) and port `6053`. Claude can also do this through HA's REST config-flow API; see
   `../CLAUDE.md`.
2. Entities: a fan **Ventilatie**, a *WiFi signaal* sensor, and a *Herstart ventilatie-bridge*
   button.
3. The fan has 4 speeds. HA percentages map to presets as follows: **25 % = low (1), 50 % = medium (2),
   75 % = high (3), 100 % = max (4)**. Turning the fan *off* sends preset `0x00`, which the code
   labels "auto/off"; check what your unit actually does with it. Each change shows up in the log as
   `Set speed: 0x02; Timer 0 minutes` followed by `Received fan settings; speed: 0x02 …`.
   Testing low/medium/high was explicitly requested as part of this task; afterwards, put the fan
   back on the speed it had.

## 8. Clean up after pairing

- In `zehnder-ventilatie.yaml`, set `logger: level:` back to `DEBUG` and delete the `logs:` block.
  Then reflash over Wi-Fi, no USB needed:
  `.venv/bin/esphome run zehnder-ventilatie.yaml --device zehnder-ventilatie.local` (or the IP).
- Record the device and entity IDs in `../docs/home-assistant.md` and
  `../docs/state-of-the-world.md`.
- Optional: the upstream example (`components_src/ESPHome-Zehnder-RF/utility-bridge.yaml`) shows
  "high for 10/30 min" timer buttons that use `zehnder_fan->setSpeed(speed, minutes)`.

## Notes for Claude (continuing this task)

- Steps 1–3 are done. Continue from step 4 and follow the project rules in `../CLAUDE.md`.
- Ask the user before every physical step: moving wires, holding BOOT, cutting the fan's power.
- Never print the contents of `secrets.yaml`. Don't commit or push.
- If a future ESPHome version breaks the build and you get stuck for more than about 5 fix attempts,
  stop, summarise the remaining errors, and ask the user how to proceed.
