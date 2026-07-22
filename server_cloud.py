"""
server_cloud.py  -  Ban "1 cong" cua server, san sang deploy len cloud FREE
(Render / Koyeb / Fly.io / Oracle ...).

Khac biet voi server_web.py: phuc vu ca HTML lan WebSocket tren CUNG 1 cong
(doc tu bien moi truong PORT). Vay chi can 1 URL, mo trinh duyet la choi duoc.

Chay local:   python server_cloud.py          (PORT mac dinh 8080)
Chay cloud:  Render tu dong set PORT, chi can `python server_cloud.py`

Yeu cau:  pip install aiohttp
"""

import asyncio
import json
import os
import time

from aiohttp import web, WSMsgType

from game_core import GameWorld, TICK

WEB_DIR = os.path.dirname(os.path.abspath(__file__))


class CloudServer:
    def __init__(self):
        self.world = GameWorld()
        self.conns = {}          # pid -> WebSocketResponse
        self.lock = asyncio.Lock()

    # --------------------- phuc vu HTML --------------------- #
    async def index(self, request):
        resp = web.FileResponse(os.path.join(WEB_DIR, "index.html"))
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return resp

    # --------------------- xu ly 1 client (WS) --------------------- #
    async def ws_handler(self, request):
        ws = web.WebSocketResponse(heartbeat=30)
        await ws.prepare(request)

        async with self.lock:
            if len(self.conns) >= 20:
                await ws.send_json({"type": "full"})
                await ws.close()
                return ws
            pid = self.world.add_player()
            self.conns[pid] = ws
        await ws.send_json({"type": "welcome", "id": pid})
        print(f"[CLOUD] Player {pid} vao phong")

        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                    except Exception:
                        continue
                    t = data.get("type")
                    if t == "input":
                        async with self.lock:
                            self.world.set_input(
                                pid, data.get("mx", 0), data.get("my", 0),
                                data.get("boost", False),
                            )
                    elif t == "join":
                        async with self.lock:
                            self.world.set_name(pid, data.get("name", ""))
                    elif t == "sac":
                        async with self.lock:
                            self.world.sacrifice(pid)
        except Exception:
            pass
        finally:
            async with self.lock:
                self.conns.pop(pid, None)
                self.world.remove_player(pid)
            print(f"[CLOUD] Player {pid} thoat")
        return ws

    # --------------------- vong lap game --------------------- #
    async def game_loop(self):
        last = time.time()
        send_acc = 0.0
        while True:
            now = time.time()
            dt = min(now - last, 0.1)
            last = now
            async with self.lock:
                self.world.step(dt)
                send_acc += dt
                if send_acc >= 0.05:
                    send_acc = 0.0
                    dead = []
                    for pid, ws in list(self.conns.items()):
                        payload = json.dumps({"type": "state", "data": self.world.serialize(pid)})
                        try:
                            await asyncio.wait_for(ws.send_str(payload), timeout=2.0)
                        except Exception:
                            dead.append(pid)
                    for pid in dead:
                        self.conns.pop(pid, None)
                        self.world.remove_player(pid)
            await asyncio.sleep(max(0.0, TICK - (time.time() - now)))

    # --------------------- dong go app --------------------- #
    def build_app(self):
        app = web.Application()
        app.router.add_get("/", self.index)
        app.router.add_get("/ws", self.ws_handler)

        async def on_startup(_app):
            _app["game"] = asyncio.create_task(self.game_loop())

        async def on_cleanup(_app):
            _app["game"].cancel()

        app.on_startup.append(on_startup)
        app.on_cleanup.append(on_cleanup)
        return app


# =============================== MAIN ================================== #
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"[CLOUD] khoi dong tai 0.0.0.0:{port}  (HTML + WS cung cong)")
    web.run_app(CloudServer().build_app(), host="0.0.0.0", port=port)
