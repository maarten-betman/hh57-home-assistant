#!/usr/bin/env python3
"""Create or complete secrets.yaml for the Zehnder bridge.

- Never overwrites an existing value; only adds keys that are missing.
- Never prints secret values.
- Wi-Fi keys get CHANGE_ME placeholders: fill them in yourself, or use the fallback hotspot.
"""
import base64
import os
import re
import secrets
import sys
from pathlib import Path

path = Path(__file__).with_name("secrets.yaml")
existing = path.read_text() if path.exists() else "# ESPHome secrets: do NOT commit or share\n"
present = set(re.findall(r"^([A-Za-z0-9_]+)\s*:", existing, flags=re.M))

wanted = {
    "wifi_ssid": lambda: "CHANGE_ME_SSID",
    "wifi_password": lambda: "CHANGE_ME_PASSWORD",
    "api_encryption_key": lambda: base64.b64encode(secrets.token_bytes(32)).decode(),
    "ota_password": lambda: secrets.token_hex(16),
    "ap_password": lambda: secrets.token_urlsafe(12),
}
added = [k for k in wanted if k not in present]
if added:
    if not existing.endswith("\n"):
        existing += "\n"
    existing += "".join(f'{k}: "{wanted[k]()}"\n' for k in added)
    old_umask = os.umask(0o077)
    try:
        path.write_text(existing)
    finally:
        os.umask(old_umask)
try:
    os.chmod(path, 0o600)
except OSError:
    pass  # e.g. Windows

placeholders = [k for k in ("wifi_ssid", "wifi_password") if "CHANGE_ME" in
                (re.search(rf'^{k}\s*:\s*(.*)$', existing, flags=re.M) or [None, ""])[1]]
print(f"{path.name}: added {', '.join(added) if added else 'nothing (all keys present)'}")
if placeholders:
    print(f"still placeholders: {', '.join(placeholders)} (edit the file, or use the fallback hotspot)")
sys.exit(0)
