"""Minimal Home Assistant websocket client for pulling long-term statistics."""
import asyncio
import itertools
import json
import os
from pathlib import Path

import websockets


def load_env():
    for line in Path(__file__).with_name(".env").read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


load_env()
HA_URL = os.environ.get("HA_URL", "http://homeassistant:8123")
WS_URL = HA_URL.replace("http", "ws", 1) + "/api/websocket"


class HA:
    async def __aenter__(self):
        self.ws = await websockets.connect(WS_URL, max_size=None)
        await self.ws.recv()  # auth_required
        await self.ws.send(json.dumps({"type": "auth", "access_token": os.environ["HA_TOKEN"]}))
        msg = json.loads(await self.ws.recv())
        if msg["type"] != "auth_ok":
            raise RuntimeError(msg)
        self.ids = itertools.count(1)
        return self

    async def __aexit__(self, *exc):
        await self.ws.close()

    async def call(self, type_, **kw):
        mid = next(self.ids)
        await self.ws.send(json.dumps({"id": mid, "type": type_, **kw}))
        while True:
            msg = json.loads(await self.ws.recv())
            if msg.get("id") == mid:
                if not msg.get("success", True):
                    raise RuntimeError(msg)
                return msg["result"]

    async def statistics(self, ids, start, end=None, period="hour", types=("change",)):
        kw = dict(start_time=start, statistic_ids=list(ids), period=period, types=list(types))
        if end:
            kw["end_time"] = end
        return await self.call("recorder/statistics_during_period", **kw)


def run(coro):
    return asyncio.run(coro)
