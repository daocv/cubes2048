"""
server_web.py  -  May chu WEB cua "Cubes 2048" (choi tren trinh duyet).

Chay:   python server_web.py [ws_port] [http_port]
Mac dinh:   ws_port = 8765,  http_port = 8080

- Phuc vu file index.html tai  http://<may-chu>:8080
- Nhan ket noi WebSocket tai    ws://<may-chu>:8765
Logic game dung chung game_core.py voi ban TCP.

Yeu cau:  pip install websockets
"""

import asyncio
import json
import os
import time
import threading
import http.server
import socketserver

import websockets

from game_core import GameWorld, TICK


class WebGameServer:
    def __init__(self, ws_host="0.0.0.0", ws_port=8765, http_port=8080,
                 web_dir=None, max_players=20):
        self.ws_host = ws_host
        self.ws_port = ws_port
        self.http_port = http_port
        self.web_dir = web_dir or os.path.dirname(os.path.abspath(__file__))
        self.max_players = max_players
        self.world = GameWorld()
        self.conns = {}          # pid -> websocket
        self.lock = asyncio.Lock()

    # --------------------- phuc vu HTML (http) --------------------- #
    def _start_http(self):
        directory = self.web_dir

        class Handler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=directory, **kwargs)

            def end_headers(self):
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                super().end_headers()

            def log_message(self, *args):
                pass  # tat log access

        httpd = socketserver.ThreadingTCPServer(("", self.http_port), Handler)
        httpd.allow_reuse_address = True
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        print(f"[WEB] HTML tai  http://localhost:{self.http_port}")

    # --------------------- xu ly 1 client (ws) --------------------- #
    async def _handler(self, ws):
        async with self.lock:
            if len(self.conns) >= self.max_players:
                await ws.send(json.dumps({"type": "full"}))
                await ws.close()
                print(f"[WEB] tu choi ket noi: phong day")
                return
            pid = self.world.add_player()
            self.conns[pid] = ws
        await ws.send(json.dumps({"type": "welcome", "id": pid}))
        print(f"[WEB] Player {pid} da vao phong")
        try:
            async for raw in ws:
                try:
                    msg = json.loads(raw)
                except Exception:
                    continue
                t = msg.get("type")
                if t == "input":
                    async with self.lock:
                        self.world.set_input(
                            pid, msg.get("mx", 0), msg.get("my", 0),
                            msg.get("boost", False),
                        )
                elif t == "join":
                    async with self.lock:
                        self.world.set_name(pid, msg.get("name", ""))
                elif t == "sac":
                    async with self.lock:
                        self.world.sacrifice(pid)
        except Exception:
            pass
        finally:
            async with self.lock:
                self.conns.pop(pid, None)
                self.world.remove_player(pid)
            print(f"[WEB] Player {pid} da thoat")

    # --------------------- vong lap game --------------------- #
    async def _game_loop(self):
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
                            await asyncio.wait_for(ws.send(payload), timeout=2.0)
                        except Exception:
                            dead.append(pid)
                    for pid in dead:
                        self.conns.pop(pid, None)
                        self.world.remove_player(pid)

            await asyncio.sleep(max(0.0, TICK - (time.time() - now)))

    # --------------------- khoi dong --------------------- #
    async def _main(self):
        self._start_http()
        async with websockets.serve(self._handler, self.ws_host, self.ws_port):
            print(f"[WEB] WebSocket tai ws://localhost:{self.ws_port}")
            print(f"[WEB] mo trinh duyet va vao http://localhost:{self.http_port}")
            await self._game_loop()

    def start(self):
        try:
            asyncio.run(self._main())
        except KeyboardInterrupt:
            print("\n[WEB] dang tat...")


# =============================== MAIN ================================== #
if __name__ == "__main__":
    import sys
    ws_port = 8765
    http_port = 8080
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        ws_port = int(sys.argv[1])
    if len(sys.argv) > 2 and sys.argv[2].isdigit():
        http_port = int(sys.argv[2])
    WebGameServer(ws_port=ws_port, http_port=http_port).start()
