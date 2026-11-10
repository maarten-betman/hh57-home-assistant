"""Minimal async client for EbV heatapp! boxes (Gateway + Control Box).

Re-implements the boxes' own web-UI auth (assets.min.js / admin.min.js):
  Control Box:
    login:   POST /api/user/token/challenge -> token
             hashed = pbkdf2(charcodes(pw), charcodes(token))
             POST /api/user/token/response  -> devicetoken_encrypted, userid
             devicetoken = AES-256-CBC-decrypt(key=sha256(pw), fixed iv)
    request: params + udid/reqcount/userid, signed with
             pbkdf2(charcodes("k=v|" for sorted keys), charcodes(devicetoken))
  Gateway admin (stateless, no login step):
    request: params + udid/userlogin, signed the same way but keyed with the
             password itself instead of a devicetoken
  pbkdf2 = PBKDF2-HMAC-SHA512, 1 iteration, 64-byte key, base64.
Only read-only endpoints are used by this integration.
"""
from __future__ import annotations

import base64
import hashlib
import time

import aiohttp
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

IV = base64.b64decode("D3GC5NQEFH13is04KD2tOg==")


class HeatappError(Exception):
    pass


def _charcodes(s: str) -> str:
    return "".join(f"{ord(c):03d}" for c in s)


def _pbkdf2(password: str, salt: str) -> str:
    key = hashlib.pbkdf2_hmac("sha512", password.encode(), salt.encode(), 1, 64)
    return base64.b64encode(key).decode()


def _aes_decrypt(password: str, b64: str) -> str:
    key = hashlib.sha256(password.encode()).digest()
    dec = Cipher(algorithms.AES(key), modes.CBC(IV)).decryptor()
    raw = dec.update(base64.b64decode(b64)) + dec.finalize()
    unpad = padding.PKCS7(128).unpadder()
    return (unpad.update(raw) + unpad.finalize()).decode()


class HeatappBox:
    def __init__(self, session: aiohttp.ClientSession, host: str, user: str,
                 password: str, gateway: bool):
        self._s, self._base = session, f"http://{host}"
        self._user, self._pw, self._gateway = user, password, gateway
        self._token: str | None = None
        self._userid = None
        self._udid = "web"
        self._reqcount = 0

    async def _post(self, path: str, data: dict) -> dict:
        async with self._s.post(self._base + path, data=data,
                                headers={"cache-control": "no-cache"},
                                timeout=aiohttp.ClientTimeout(total=20)) as r:
            r.raise_for_status()
            body = await r.json(content_type=None)
        if not body or not body.get("success"):
            raise HeatappError(f"{path}: {body and body.get('message')}")
        return body

    async def login(self) -> None:
        if self._gateway:
            self._token = self._pw
            return
        ch = await self._post("/api/user/token/challenge", {"udid": "web"})
        token = ch["devicetoken"]
        hashed = _pbkdf2(_charcodes(self._pw), _charcodes(token))
        resp = await self._post("/api/user/token/response", {
            "login": self._user, "devicename": "HomeAssistant", "token": token,
            "hashed": hashed, "udid": "web"})
        self._token = _aes_decrypt(self._pw, resp["devicetoken_encrypted"])
        self._userid = resp["userid"]
        self._udid = resp.get("udid", "web")
        self._reqcount = int(resp.get("reqcount") or 0)

    def _sign(self, params: dict) -> dict:
        if self._gateway:
            data = {**params, "udid": "web", "userlogin": self._user.lower()}
        else:
            data = {**params, "udid": self._udid, "reqcount": self._reqcount,
                    "userid": self._userid}
            self._reqcount += 1
        sig = "".join(f"{k}={data[k]}|" for k in sorted(data))
        data["request_signature"] = _pbkdf2(_charcodes(sig), _charcodes(self._token))
        return data

    async def get(self, path: str, params: dict | None = None) -> dict:
        """Signed request; logs in (again) when needed."""
        for attempt in (0, 1):
            if self._token is None:
                await self.login()
            try:
                return await self._post(path, self._sign(params or {}))
            except (HeatappError, aiohttp.ClientResponseError):
                if attempt:
                    raise
                self._token = None  # session expired / counter out of sync


async def fetch_rooms(gw: HeatappBox, cb: HeatappBox) -> dict:
    """Merge gateway sensor data with Control Box room targets/status."""
    allmodules = (await gw.get("/api/gateway/allmodules"))["modules"]["rooms"]
    dbmodules = (await gw.get("/api/gateway/dbmodules"))["modules"]
    groups = (await cb.get("/api/room/list"))["groups"]
    targets = {r["name"]: r for g in groups for r in g["rooms"]}
    known = {k[2:] for k in dbmodules}
    rooms = {}
    for rid, r in allmodules.items():
        mods = list(r["modules"].values())
        sensor = next((dbmodules.get(m["id"], {}) for m in mods if m["type"] == "sensor"), {})
        cbr = targets.get(r["name"], {})
        last = sensor.get("lastResponse")
        temp = sensor.get("currentTemperature")
        rooms[rid] = {
            "name": r["name"],
            "temperature": temp if isinstance(temp, (int, float)) else None,
            "battery": sensor.get("battery"),
            "last_seen_min": round((time.time() - last / 1000) / 60) if last else None,
            "target": cbr.get("desiredTemperature"),
            "target_day": cbr.get("desiredTempDay"),
            "target_night": cbr.get("desiredTempNight"),
            "min": r["minTemperature"], "max": r["maxTemperature"],
            "status": cbr.get("status") or "unknown",
            "missing_actuators": [m["id"] for m in mods if m["type"] != "sensor"
                                  and m["id"][2:] not in known and m["status"] != 0],
        }
    hw = targets.get("hot water") or {}
    return {"rooms": rooms, "hot_water": {
        "target": hw.get("desiredTemperature"), "target_day": hw.get("desiredTempDay"),
        "target_night": hw.get("desiredTempNight"), "temperature": hw.get("actualTemperature")}}
