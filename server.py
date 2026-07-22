"""
server.py  -  May chu TCP cua "Cubes 2048" (2 nguoi choi).

Chay:   python server.py [port]      (mac dinh port 5555)
May chu la trong tai duy nhat: nhan dieu khien tu 2 client, tinh toan
bang game_core.py va dong bo trang thai ve ca hai o 60 lan/giay.
"""

import socket
import struct
import json
import time
import threading

from game_core import GameWorld, TICK


# ===================== GOI TIN (length-prefixed JSON) ==================== #
def _recvn(sock, n):
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            return None
        buf.extend(chunk)
    return bytes(buf)


def send_msg(sock, obj):
    try:
        data = json.dumps(obj).encode("utf-8")
        sock.sendall(struct.pack("!I", len(data)) + data)
        return True
    except Exception:
        return False


def recv_msg(sock):
    raw = _recvn(sock, 4)
    if raw is None:
        return None
    (length,) = struct.unpack("!I", raw)
    data = _recvn(sock, length)
    if data is None:
        return None
    try:
        return json.loads(data.decode("utf-8"))
    except Exception:
        return None


# ============================ MAY CHU TCP ============================== #
class GameServer:
    def __init__(self, host="0.0.0.0", port=5555, max_players=20):
        self.host = host
        self.port = port
        self.max_players = max_players
        self.world = GameWorld()
        self.conns = {}        # pid -> socket
        self.lock = threading.Lock()
        self.running = False
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def start(self):
        self.sock.bind((self.host, self.port))
        self.sock.listen(2)
        self.running = True
        print(f"[SERVER] lang nghe TCP tai {self.host}:{self.port}")
        threading.Thread(target=self._accept_loop, daemon=True).start()
        try:
            self._game_loop()
        except KeyboardInterrupt:
            print("\n[SERVER] dang tat...")
        finally:
            self.running = False
            try:
                self.sock.close()
            except Exception:
                pass

    def _accept_loop(self):
        while self.running:
            try:
                conn, addr = self.sock.accept()
            except OSError:
                break
            conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            with self.lock:
                if len(self.conns) >= self.max_players:
                    send_msg(conn, {"type": "full"})
                    try:
                        conn.close()
                    except Exception:
                        pass
                    print(f"[SERVER] tu choi {addr}: phong day")
                    continue
                pid = self.world.add_player()
                self.conns[pid] = conn
            send_msg(conn, {"type": "welcome", "id": pid})
            print(f"[SERVER] Player {pid} ket noi tu {addr}")
            threading.Thread(
                target=self._client_handler, args=(conn, pid), daemon=True
            ).start()

    def _client_handler(self, conn, pid):
        try:
            while self.running:
                msg = recv_msg(conn)
                if msg is None:
                    break
                t = msg.get("type")
                if t == "input":
                    with self.lock:
                        self.world.set_input(
                            pid, msg.get("mx", 0), msg.get("my", 0),
                            msg.get("boost", False),
                        )
                elif t == "join":
                    with self.lock:
                        self.world.set_name(pid, msg.get("name", ""))
                elif t == "sac":
                    with self.lock:
                        self.world.sacrifice(pid)
        except Exception:
            pass
        finally:
            self._disconnect(pid)
            print(f"[SERVER] Player {pid} da ngat ket noi")

    def _disconnect(self, pid):
        with self.lock:
            self.conns.pop(pid, None)
            self.world.remove_player(pid)

    def _game_loop(self):
        last = time.time()
        while self.running:
            now = time.time()
            frame = min(now - last, 0.1)
            last = now

            with self.lock:
                self.world.step(frame)
                dead = []
                for pid in list(self.conns.keys()):
                    conn = self.conns.get(pid)
                    if conn is None:
                        continue
                    state = self.world.serialize(pid)
                    if not send_msg(conn, {"type": "state", "data": state}):
                        dead.append(pid)
                for pid in dead:
                    self.conns.pop(pid, None)
                    self.world.remove_player(pid)

            sleep = TICK - (time.time() - now)
            if sleep > 0:
                time.sleep(sleep)


# =============================== MAIN ================================== #
if __name__ == "__main__":
    import sys
    port = 5555
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        port = int(sys.argv[1])
    GameServer(port=port).start()
