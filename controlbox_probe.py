#!/usr/bin/env .venv/bin/python
"""Read-only probe of the alpha home Control Box (192.168.2.3).

Logs in with the device's normal challenge/response flow using the credentials
in .env (CONTROLBOX_USER / CONTROLBOX_PASS) and fetches configuration read-only.
Makes no settings changes. Prints what it finds about hot-water (warmwater) control.
"""
import os, json, hashlib, urllib.request, urllib.error
from ha import load_env

load_env()
BASE = "http://192.168.2.3"
USER = os.environ["CONTROLBOX_USER"]
PW = os.environ["CONTROLBOX_PASS"]


def post(path, body):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:300]


def main():
    code, ch = post("/api/user/token/challenge", {"udid": "web"})
    tok = ch.get("devicetoken") if isinstance(ch, dict) else None
    print(f"challenge: http {code} success={ch.get('success') if isinstance(ch,dict) else ch}")
    if not tok:
        print("no token; stopping"); return
    md5 = lambda s: hashlib.md5(s.encode()).hexdigest()
    schemes = {
        "md5(pw+token)": md5(PW + tok),
        "md5(md5(pw)+token)": md5(md5(PW) + tok),
    }
    ok = False
    for name, hashed in schemes.items():
        code, resp = post("/api/user/token/response",
                          {"login": USER, "devicename": "Computer",
                           "token": tok, "hashed": hashed, "udid": "web"})
        ok = resp.get("success") if isinstance(resp, dict) else None
        rej = resp.get("loginRejected") if isinstance(resp, dict) else None
        msg = resp.get("message") if isinstance(resp, dict) else resp
        print(f"login [{name}]: http {code} success={ok} loginRejected={rej} message={msg!r}")
        if ok:
            break
    if not ok:
        print("\nno known hash scheme accepted; stopping (would need the crypto bundle to match)"); return

    # Try read-only admin endpoints several auth shapes
    session = {"udid": "web", "login": USER, "token": tok, "devicetoken": tok}
    for ep in ["systeminformation/get", "heatapp/getconfiguration", "portal/get"]:
        code, data = post("/admin/" + ep, session)
        if isinstance(data, dict):
            print(f"\n/admin/{ep}: http {code} keys={list(data.keys())}")
            print(json.dumps(data, indent=2, ensure_ascii=False)[:1500])
        else:
            print(f"\n/admin/{ep}: http {code} -> {data}")


main()
