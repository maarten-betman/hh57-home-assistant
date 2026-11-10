#!/usr/bin/env .venv/bin/python
"""Upload custom_components/<name>/ to HA's /config via the File editor add-on.

HA OS has no SSH port open here, so this goes through the File editor
(core_configurator) ingress API: a supervisor ingress session cookie, then
its /api/newfolder and /api/save endpoints. Restart HA afterwards to load
a new integration.

Usage: .venv/bin/python deploy_custom_component.py heatapp_rooms
"""
import json, os, sys, urllib.parse, urllib.request
from pathlib import Path
from ha import HA, load_env, run

load_env()
URL = os.environ["HA_URL"]
ROOT = "/homeassistant"  # how the File editor add-on sees HA's /config


async def main(name):
    async with HA() as h:
        info = await h.call("supervisor/api", method="get",
                            endpoint="/addons/core_configurator/info")
        entry = info["ingress_entry"]
        sess = (await h.call("supervisor/api", endpoint="/ingress/session",
                             method="post"))["session"]

    def post(path, fields):
        req = urllib.request.Request(
            URL + entry + path, data=urllib.parse.urlencode(fields).encode(),
            headers={"Cookie": f"ingress_session={sess}"}, method="POST")
        return urllib.request.urlopen(req, timeout=20).read().decode()

    def listdir(path):
        req = urllib.request.Request(
            URL + entry + "/api/listdir?" + urllib.parse.urlencode({"path": path}),
            headers={"Cookie": f"ingress_session={sess}"})
        body = json.loads(urllib.request.urlopen(req, timeout=20).read())
        return {e["name"] for e in body.get("content", [])}

    src = Path("custom_components") / name
    for d in [f"{ROOT}/custom_components", f"{ROOT}/custom_components/{name}"] + [
            f"{ROOT}/custom_components/{name}/{p.relative_to(src)}"
            for p in src.rglob("*") if p.is_dir() and "__pycache__" not in p.parts]:
        parent, leaf = d.rsplit("/", 1)
        if leaf not in listdir(parent):
            print("mkdir", d, post("/api/newfolder", {"path": parent, "name": leaf}))
    for f in sorted(src.rglob("*")):
        if f.is_file() and "__pycache__" not in f.parts:
            dest = f"{ROOT}/custom_components/{name}/{f.relative_to(src)}"
            print("save", dest, post("/api/save", {"filename": dest, "text": f.read_text()}))


run(main(sys.argv[1]))
