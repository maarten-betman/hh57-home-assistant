# Zehnder ComfoFan S: ESPHome RF bridge (ESP32 + nRF905)

Makes an ESP32 act as a Zehnder RFZ remote over an nRF905 radio (868 MHz, channel 118), so
Home Assistant can control the ComfoFan S R. It uses the external component
`Sanderhuisman/ESPHome-Zehnder-RF`, ported locally to ESPHome 2026.x.

## Status (2026-11-10)

| Step | State |
|---|---|
| 1. Project, venv, secrets | ✅ done on the second laptop (ESPHome **2026.10.2**). Wi-Fi credentials filled in. |
| 2. Compile | ✅ compiles. Upstream fails (`fan.FanState` removed); the local port works. See `PATCHES.md`. |
| 3. Port component + bug fixes | ✅ done; diff in `patches/zehnder-rf-esphome-2026.patch` |
| 4. Flash over USB | ✅ flashed 2026-11-10 from Windows with esptool (no admin needed, see step 4). |
| 5. nRF905 init check | ✅ `Write config OK`, `nRF905 Setup complete`. SPI wiring is good. |
| 6. Pairing with the fan | ✅ paired 2026-11-10 22:40 (network `0x206C9815`, main unit type 0x01 ID 0x59, we are type 0x03 ID 0x0A). Survives reboots. |
| 7. Add to Home Assistant | ✅ added 2026-11-10 via the zeroconf-discovered config flow. Entities below. |
| 8. Clean-up (logger DEBUG, OTA) | ✅ logger back to DEBUG, OTA-flashed 22:53. Speeds 1→2→3→1 tested from HA; the fan confirmed each (30/50/90 % voltage). |

**Done.** Remaining: pick a permanent spot for the board (see "Placement" under step 6).

The device is on Wi-Fi as `zehnder-ventilatie` (IP **192.168.2.45** at the time of writing, MAC
`B0:3F:D3:51:E4:30`). From now on it can be flashed over the air; USB is no longer needed.

HA: device `Ventilatie` (config entry `01M73N5DP364E1SXBJZNAN8BAN`), entities
`fan.ventilatie_ventilatie`, `sensor.ventilatie_wifi_signaal`, `button.ventilatie_herstart_ventilatie_bridge`,
`button.ventilatie_hoog_10_minuten`, `button.ventilatie_hoog_30_minuten`.

## Files

| Path | What |
|---|---|
| `zehnder-ventilatie.yaml` | The device config. Logger at DEBUG (was VERBOSE during pairing). |
| `secrets.yaml` | **git-ignored, private.** Wi-Fi, API encryption key, OTA and AP passwords. |
| `secrets.example.yaml` | The keys `secrets.yaml` must contain. |
| `make_secrets.py` | Creates or completes `secrets.yaml` with random keys. Never overwrites, never prints values. |
| `requirements.txt` | `esphome==2026.10.2` (pinned: the port was built and tested against this version). |
| `serial_log.py` | Tiny pyserial script: resets the board and streams the serial log to a file with timestamps. Used from Windows when WSL can't see the USB port (step 4). |
| `components_src/ESPHome-Zehnder-RF/` | Upstream clone @ `7d6de29` with the port applied (uncommitted, branch `esphome-2026-port`). The main repo only records it as a bare gitlink, so on a fresh checkout the folder is **empty**: rebuild it (step 0.3). |
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

**Pitfall (Ubuntu/WSL):** ESPHome 2026.x builds the Arduino framework on top of ESP-IDF and creates its
own Python venv for it with `python -m venv`. If the base interpreter has no `ensurepip` (Ubuntu's
`python3` without `python3.12-venv`), compile dies with `Can't create Python virtual environment for
ESP-IDF 5.5.6`. Without sudo, the fix is to build `.venv` on a uv-managed Python instead:
```bash
uv python install 3.12
uv venv .venv --python "$(uv python find 3.12 --managed-python)"
uv pip install --python .venv/bin/python -r requirements.txt
```
The ESP-IDF toolchain lands in `~/.cache/esphome/idf/` (first compile downloads ~300 MB).

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

**WSL2 without admin for usbipd (what we actually did):** compile in WSL, flash from Windows with
esptool in a Windows venv. Needs only `uv.exe` (user install) and the CH340 driver (Windows Update
installed it by itself within a minute of plugging in; before that the device showed as *USB Serial*
with a driver error and no COM port).
```bash
# one-time, from WSL (Windows paths, because uv.exe runs on Windows)
cmd.exe /c "C:\Users\betman\.local\bin\uv.exe venv C:\Users\betman\zehnder-flash\.venv --python 3.12"
cmd.exe /c "C:\Users\betman\.local\bin\uv.exe pip install --python C:\Users\betman\zehnder-flash\.venv\Scripts\python.exe esptool==5.4.0 pyserial"
cp serial_log.py /mnt/c/Users/betman/zehnder-flash/
# every flash
cp .esphome/build/zehnder-ventilatie/build/firmware.factory.bin /mnt/c/Users/betman/zehnder-flash/
cmd.exe /c "C:\Users\betman\zehnder-flash\.venv\Scripts\esptool.exe --port COM4 --chip esp32 --baud 460800 write-flash 0x0 C:\Users\betman\zehnder-flash\firmware.factory.bin"
# serial log for 60 s into boot.log (resets the board first)
cmd.exe /c "C:\Users\betman\zehnder-flash\.venv\Scripts\python.exe C:\Users\betman\zehnder-flash\serial_log.py COM4 115200 C:\Users\betman\zehnder-flash\boot.log 60"
sed 's/\x1b\[[0-9;]*m//g' /mnt/c/Users/betman/zehnder-flash/boot.log | less
```
Find the COM port with `powershell.exe -c "[System.IO.Ports.SerialPort]::GetPortNames()"`. Auto-reset
via DTR/RTS works on this board; the BOOT button was never needed.

**Browser alternative:** Chrome or Edge at <https://web.esphome.io> → *Connect* → pick the CH340 port →
*Install* → choose `.esphome/build/zehnder-ventilatie/build/firmware.factory.bin`. Its *Logs* view
shows the serial output.

**Observed Wi-Fi quirk:** with the `CHANGE_ME` placeholders the ESP reported `Scan done: number=0` on
every scan and never showed the fallback hotspot, even after 100 s. With the real SSID/password in
`secrets.yaml` it found the network and connected within 8 s of boot. So option B above is unverified;
prefer option A. (`ap_timeout:` belongs *inside* the `ap:` block, not at `wifi:` level.)

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

**How it actually went (2026-11-10):** the fan answers the discovery broadcast, the ESP sends a join
request, the fan replies `0x0B` (link successful) and the ESP acknowledges with `0x0B`. The component
then waits for a `0x0D` frame before saving. The fan sends that only sometimes: three link attempts
in a row ended in `Received unknown frame type 0x0B` (the fan repeating its 0x0B) followed by
`Query Timeout`, and the fourth got the 0x0D and saved. The fan kept accepting new join requests for
the whole 10-minute window, so just let it loop. Expect `Saving pairing config` / `join success` to be
missing from a Wi-Fi log at VERBOSE level: the log stream drops lines under load. The proof is
`Current state: 0x06` followed by `Received fan settings` and, after a reboot, `Config data valid`.

**Placement:** the board paired next to the fan but did **not** get a reply from the laptop desk during
the first attempt; after pairing, queries from the desk timed out several times and then started
working. So the desk is at the edge of RF range. Put the board somewhere between, with Wi-Fi better
than about -70 dBm. **Don't power it from the fan's circuit:** the first pairing attempt failed because
the ESP lost power together with the fan.

**Safe mode:** if the board pings and port 3232 (OTA) is open but port 6053 (API) refuses, ESPHome is in
*safe mode* after repeated failed boots (it happened at 23:09 after several re-plugs and power drops at
the fan). Any OTA upload (`esphome upload … --device <ip>`) brings it back; the log then shows
`Boot seems successful; resetting boot loop counter`. If it recurs at the same spot, suspect the USB
charger (brownouts during Wi-Fi bursts).

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
   (or its IP) and port `6053`. Claude can also do this through HA's REST config-flow API (done on
   2026-11-10: list flows with websocket `config_entries/flow/progress`, then `POST
   /api/config/config_entries/flow/<id>` with `{}` for `discovery_confirm` and `{"noise_psk": key}`
   for `encryption_key`). Without HA, the API can be checked directly from the venv with
   `aioesphomeapi` (`APIClient(host, 6053, None, noise_psk=key)`; `device_info()`, `list_entities_services()`).
2. Entities: a fan **Ventilatie**, a *WiFi signaal* sensor, and a *Herstart ventilatie-bridge*
   button.
3. The fan has 4 speeds. HA percentages map to presets as follows: **25 % = low (1), 50 % = medium (2),
   75 % = high (3), 100 % = max (4)**. Turning the fan *off* sends preset `0x00`, which the code
   labels "auto/off"; check what your unit actually does with it. Each change shows up in the log as
   `Set speed: 0x02; Timer 0 minutes` followed by `Received fan settings; speed: 0x02 …`.
   Tested 2026-11-10: speeds 1–3 and the 10-minute boost (`speed: 0x03 … timer: 1`) are each confirmed
   by the fan within 0.3 s when the board is near the fan. **Speed 0 is not off:** the fan accepts it and
   reports `speed: 0x00 voltage: 30`, i.e. its lowest/"away" setting. The dashboard tile therefore opens
   more-info on tap instead of toggling.

## 8. Clean up after pairing

- ✅ Logger set back to `DEBUG`, flashed over Wi-Fi with
  `.venv/bin/esphome upload zehnder-ventilatie.yaml --device 192.168.2.45` (62 s).
- ✅ Device and entity IDs recorded in `../docs/home-assistant.md` and `../docs/state-of-the-world.md`.
- Cosmetic: the nRF905 log line `Channel 118 Band 868 MHz -> 433200000` shows a stale `frequency`
  field (only recomputed when registers are read back). The band bit is correct; ignore it.
- ✅ Timer buttons added (2026-11-10): `button.ventilatie_hoog_10_minuten` and
  `button.ventilatie_hoog_30_minuten` (template buttons calling `zehnder_fan->setSpeed(3, minutes)`).
  Also on the Mobiel dashboard: Thuis view, section **Ventilatie** (fan tile with speed selector plus the
  two boost tiles). Backup: `../backups/mobiel-dashboard-before-ventilatie.json`.

## Notes for Claude (continuing this task)

- All steps are done (2026-11-10), including the timer buttons and the dashboard section. Open item:
  permanent placement of the board.
- To re-pair (new fan, or after `erase-flash`): power-cycle the fan with the ESP powered from
  elsewhere and within a few metres; it pairs by itself within the fan's 10-minute window.
- Since the board is on Wi-Fi, reflash with
  `.venv/bin/esphome run zehnder-ventilatie.yaml --device 192.168.2.45` (OTA) and read logs with
  `.venv/bin/esphome logs zehnder-ventilatie.yaml --device 192.168.2.45`; no Windows detour needed.
- The project's own `.venv` (for `ha.py`) doesn't exist on the second laptop; `esphome/.venv/bin/python`
  has `websockets` and works for `ha.py` scripts.
- Ask the user before every physical step: moving wires, holding BOOT, cutting the fan's power.
- Never print the contents of `secrets.yaml`. Don't commit or push.
- If a future ESPHome version breaks the build and you get stuck for more than about 5 fix attempts,
  stop, summarise the remaining errors, and ask the user how to proceed.
