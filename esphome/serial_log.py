"""Stream serial output from the ESP32 to a log file with timestamps.
Usage: python serial_log.py COM4 115200 out.log [seconds]
Reset the board on open (pulses DTR/RTS like esptool/esphome do), so the boot log is captured.
"""
import sys, time, serial
port, baud, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
limit = float(sys.argv[4]) if len(sys.argv) > 4 else None
ser = serial.Serial(port, baud, timeout=1)
# Reset: EN low via RTS, keep IO0 high (DTR false) so it boots normally, not into the bootloader.
ser.dtr = False; ser.rts = True; time.sleep(0.1); ser.rts = False
t0 = time.time()
with open(out, "a", encoding="utf-8", errors="replace") as f:
    f.write(f"=== opened {port} @ {baud} {time.strftime('%Y-%m-%d %H:%M:%S')}\n"); f.flush()
    buf = b""
    while limit is None or time.time() - t0 < limit:
        data = ser.read(4096)
        if not data:
            continue
        buf += data
        while b"\n" in buf:
            line, buf = buf.split(b"\n", 1)
            f.write(f"{time.time()-t0:8.2f} {line.decode('utf-8','replace').rstrip()}\n")
        f.flush()
