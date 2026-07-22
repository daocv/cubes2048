"""
client.py  -  May tram nguoi choi "Cubes 2048" (Pygame + mang TCP).

Chay:   python client.py
Man hinh dau tien nhap IP/Port cua server, sau do vao choi.
- Dieu khien huong bang chuot (ran luoi theo con tro).
- Tang toc: chuot trai hoac Space (tieu ton thanh nang luong).
"""

import socket
import struct
import json
import math
import sys
import threading
import random
import colorsys
import pygame

# ============================== HE SO GAME ============================== #
MAP_W, MAP_H = 6000, 6000
CUBE = 40
WIDTH, HEIGHT = 960, 640
FPS = 60
ENERGY_MAX = 100.0

# Bang mau chuan 2048 (fill, text)
COLORS = {
    2: (238, 228, 218),    4: (237, 224, 200),    8: (242, 177, 121),
    16: (245, 149, 99),    32: (246, 124, 95),    64: (246, 94, 59),
    128: (237, 207, 114),  256: (237, 204, 97),   512: (237, 200, 80),
    1024: (237, 197, 63),  2048: (237, 194, 46),
}


def cube_color(v):
    return COLORS.get(v, (60, 58, 50))


def text_color(v):
    return (119, 110, 101) if v <= 4 else (249, 246, 242)


def fmt_num(v):
    a = abs(v)
    if a >= 1e9:
        s = f"{v/1e9:.1f}" if a < 1e10 else f"{v/1e9:.0f}"
        return s.rstrip("0").rstrip(".") + "B"
    if a >= 1e6:
        s = f"{v/1e6:.1f}" if a < 1e7 else f"{v/1e6:.0f}"
        return s.rstrip("0").rstrip(".") + "M"
    if a >= 1e3:
        s = f"{v/1e3:.1f}" if a < 1e4 else f"{v/1e3:.0f}"
        return s.rstrip("0").rstrip(".") + "K"
    return str(v)


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


# =============================== CAMERA ================================= #
class Camera:
    """Camera di chuyen mem, lay dau ran nguoi choi lam trung tam."""
    def __init__(self, w, h):
        self.x = 0.0
        self.y = 0.0
        self.w = w
        self.h = h

    def follow(self, tx, ty, dt):
        k = min(1.0, dt * 8.0)
        self.x += (tx - self.w / 2 - self.x) * k
        self.y += (ty - self.h / 2 - self.y) * k

    def to_screen(self, wx, wy):
        return (wx - self.x, wy - self.y)


# ============================== VE KHOI ================================ #
def player_edge(pid):
    """Mau vien rieng cho tung nguoi choi (dua tren pid)."""
    h = ((pid * 47) % 360) / 360.0
    r, g, b = colorsys.hls_to_rgb(h, 0.62, 0.78)
    return (int(r * 255), int(g * 255), int(b * 255))


DRAGON_STYLES = {
    "DAOCV":  dict(edge=(255,217,94),  aura=(255,140,0),   horn=(255,217,94),  eye=(255,68,68),
                   fin=(255,217,94),   horn_type="curve"),
    "KID":    dict(edge=(127,208,255), aura=(0,160,255),   horn=(143,234,255), eye=(68,255,255),
                   fin=(127,208,255),  horn_type="spike"),
    "MAPDIA": dict(edge=(199,94,255),  aura=(140,0,200),   horn=(199,94,255),  eye=(255,68,255),
                   fin=(199,94,255),   horn_type="twist"),
}


def dragon_style(p):
    return DRAGON_STYLES.get(p.get("name", "").upper())


def is_dragon(p):
    return dragon_style(p) is not None


def draw_cube(surf, cam, cx, cy, value, is_head=False, edge=(255, 255, 255)):
    sx, sy = cam.to_screen(cx, cy)
    # bo ve nhung khoi ngoai man hinh
    if sx < -CUBE or sx > WIDTH + CUBE or sy < -CUBE or sy > HEIGHT + CUBE:
        return
    rect = pygame.Rect(0, 0, CUBE, CUBE)
    rect.center = (int(sx), int(sy))
    fill = cube_color(value)
    pygame.draw.rect(surf, fill, rect, border_radius=6)
    # vien
    pygame.draw.rect(surf, edge, rect, 3 if is_head else 2, border_radius=6)
    # so giua khoi
    font = _font_for(value)
    text = font.render(fmt_num(value), True, text_color(value))
    surf.blit(text, text.get_rect(center=rect.center))


_font_cache = {}


def _font_for(value):
    if value not in _font_cache:
        size = 22 if value < 100 else (18 if value < 1000 else (14 if value < 1e6 else (12 if value < 1e9 else 10)))
        _font_cache[value] = pygame.font.SysFont("consolas", size, bold=True)
    return _font_cache[value]


# =========================== MAN HINH KET NOI ========================== #
def try_connect(ip, port):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        s.connect((ip, port))
        s.settimeout(None)
        s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        return s
    except Exception:
        return None


def connect_screen(win, clock):
    """Nhap Ten + IP + Port. Tra ve (socket, pid)."""
    font = pygame.font.SysFont("consolas", 30, bold=True)
    lab = pygame.font.SysFont("consolas", 22)
    fields = ["", "127.0.0.1", "5555"]   # 0: ten, 1: IP, 2: port
    active = 1
    err = ""
    title = "CUBES 2048 - KET NOI SERVER"

    boxes = [
        pygame.Rect(WIDTH // 2 - 160, 170, 320, 44),  # Ten
        pygame.Rect(WIDTH // 2 - 160, 260, 320, 44),  # IP
        pygame.Rect(WIDTH // 2 - 160, 350, 320, 44),  # Port
    ]
    labels = ["Ten cua ban:", "Dia chi IP:", "Port:"]
    placeholders = ["vd: Pro_Snake", "vd: 127.0.0.1", "vd: 5555"]

    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif e.type == pygame.MOUSEBUTTONDOWN:
                for i, b in enumerate(boxes):
                    if b.collidepoint(e.pos):
                        active = i
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_TAB:
                    active = (active + 1) % 3
                elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    port = int(fields[2]) if fields[2].isdigit() else 5555
                    s = try_connect(fields[1], port)
                    if s is None:
                        err = "Khong ket noi duoc. Kiem tra IP/Port va server."
                    else:
                        wel = recv_msg(s)
                        if wel and wel.get("type") == "welcome":
                            nm = fields[0].strip()[:12] or ("P%d" % wel["id"])
                            send_msg(s, {"type": "join", "name": nm})
                            return s, wel["id"]
                        err = "Server khong phan hoi dung."
                        try:
                            s.close()
                        except Exception:
                            pass
                elif e.key == pygame.K_BACKSPACE:
                    fields[active] = fields[active][:-1]
                else:
                    ch = e.unicode
                    if ch and ch.isprintable():
                        if active == 2 and not ch.isdigit():
                            continue
                        limit = 12 if active == 0 else (21 if active == 1 else 6)
                        if len(fields[active]) < limit:
                            fields[active] += ch

        # ---- ve ---- #
        win.fill((30, 32, 40))
        win.blit(font.render(title, True, (240, 240, 240)),
                 (WIDTH // 2 - font.size(title)[0] // 2, 100))
        for i, box in enumerate(boxes):
            win.blit(lab.render(labels[i], True, (180, 180, 180)),
                     (box.x, box.y - 24))
            col = (90, 160, 240) if i == active else (70, 70, 80)
            pygame.draw.rect(win, (50, 52, 62), box, border_radius=6)
            pygame.draw.rect(win, col, box, 2, border_radius=6)
            txt = fields[i] if fields[i] else placeholders[i]
            tcol = (240, 240, 240) if fields[i] else (110, 110, 120)
            win.blit(font.render(txt, True, tcol), (box.x + 12, box.y + 8))

        hint = "ENTER de ket noi  |  TAB chuyen o"
        win.blit(lab.render(hint, True, (140, 140, 150)),
                 (WIDTH // 2 - lab.size(hint)[0] // 2, 420))
        if err:
            win.blit(lab.render(err, True, (240, 90, 90)),
                     (WIDTH // 2 - lab.size(err)[0] // 2, 460))
        pygame.display.flip()
        clock.tick(FPS)


# ================================ GAME ================================= #
class Game:
    def __init__(self, sock, pid):
        self.sock = sock
        self.pid = pid            # 1 hoac 2
        self.state = None
        self.lock = threading.Lock()
        self.running = True
        self.cam = Camera(WIDTH, HEIGHT)
        threading.Thread(target=self._recv_loop, daemon=True).start()

    def _recv_loop(self):
        try:
            while self.running:
                msg = recv_msg(self.sock)
                if msg is None:
                    break
                if msg.get("type") == "state":
                    with self.lock:
                        self.state = msg["data"]
        except Exception:
            pass
        self.running = False

    # ---- tien ich lay trang thai ---- #
    def get_snake(self, pid):
        if not self.state:
            return None
        for p in self.state.get("players", []):
            if p["id"] == pid:
                return p
        return None

    def me(self):
        return self.get_snake(self.pid)

    def all_players(self):
        if not self.state:
            return []
        return self.state.get("players", [])

    # =========================== VONG LAP CHINH =========================== #
    def loop(self, win, clock):
        font = pygame.font.SysFont("consolas", 20, bold=True)
        big = pygame.font.SysFont("consolas", 30, bold=True)

        while self.running:
            dt = clock.tick(FPS) / 1000.0

            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    self.running = False
                elif e.type == pygame.KEYDOWN and e.key == pygame.K_e:
                    send_msg(self.sock, {"type": "sac"})

            boost = pygame.mouse.get_pressed()[0] or pygame.key.get_pressed()[pygame.K_SPACE]

            # huong = mui ten / WASD; neu khong thi theo chuot
            k = pygame.key.get_pressed()
            dx = dy = 0
            if k[pygame.K_LEFT] or k[pygame.K_a]:
                dx -= 1
            if k[pygame.K_RIGHT] or k[pygame.K_d]:
                dx += 1
            if k[pygame.K_UP] or k[pygame.K_w]:
                dy -= 1
            if k[pygame.K_DOWN] or k[pygame.K_s]:
                dy += 1

            with self.lock:
                state = self.state

            me = self.me()
            if dx or dy:
                if me and me["cubes"]:
                    hx, hy, _ = me["cubes"][0]
                    world_x = hx + dx * 1000
                    world_y = hy + dy * 1000
                else:
                    mx, my = pygame.mouse.get_pos()
                    world_x = mx + self.cam.x
                    world_y = my + self.cam.y
            else:
                mx, my = pygame.mouse.get_pos()
                world_x = mx + self.cam.x
                world_y = my + self.cam.y

            # gui dieu khien len server (luon gui, ca khi chet)
            if not send_msg(self.sock, {"type": "input",
                                        "mx": world_x, "my": world_y,
                                        "boost": bool(boost)}):
                self.running = False

            # ---- ve ---- #
            self._draw(win, font, big, state, dt)
            pygame.display.flip()

        # da ngat ket noi
        self._show_disconnected(win, big)

    def _draw(self, win, font, big, state, dt):
        win.fill((24, 26, 34))

        # camera theo dau cua minh
        me = self.me()
        if me and me["cubes"]:
            hx, hy, _ = me["cubes"][0]
            self.cam.follow(hx, hy, dt)

        self._draw_grid(win)
        self._draw_map_border(win)

        # vat can
        if state:
            for ob in state.get("obstacles", []):
                self._draw_obstacle(win, ob[0], ob[1], ob[2],
                                    ob[3] if len(ob) > 3 else "red",
                                    ob[4] if len(ob) > 4 else "square")

        # khoi tu do
        if state:
            for f in state.get("foods", []):
                fx, fy, val = f[0], f[1], f[2]
                sx, sy = self.cam.to_screen(fx, fy)
                if -CUBE <= sx <= WIDTH + CUBE and -CUBE <= sy <= HEIGHT + CUBE:
                    is_death = len(f) > 3
                    alpha = min(1.0, f[3] / 1.5) if is_death else 1.0
                    r = pygame.Rect(0, 0, int(CUBE * 0.7), int(CUBE * 0.7))
                    r.center = (int(sx), int(sy))
                    if alpha < 1.0:
                        surf = pygame.Surface((r.w + 4, r.h + 4), pygame.SRCALPHA)
                        r2 = pygame.Rect(2, 2, r.w, r.h)
                        pygame.draw.rect(surf, (*cube_color(val), int(255 * alpha)), r2, border_radius=5)
                        pygame.draw.rect(surf, (255, 107, 107, int(255 * alpha)), r2, 1, border_radius=5)
                        win.blit(surf, (r.x - 2, r.y - 2))
                    else:
                        pygame.draw.rect(win, cube_color(val), r, border_radius=5)
                        pygame.draw.rect(win, (90, 80, 70), r, 1, border_radius=5)

        # powerups
        if state:
            for px, py, pkind, prem in state.get("powerups", []):
                self._draw_powerup(win, px, py, pkind, prem)

        # tat ca nguoi choi
        for p in self.all_players():
            if not p.get("cubes"):
                continue
            ds = dragon_style(p)
            edge = ds["edge"] if ds else ((255, 255, 255) if p["id"] == self.pid else player_edge(p["id"]))
            for i, (cx, cy, val) in enumerate(p["cubes"]):
                draw_cube(win, self.cam, cx, cy, val, is_head=(i == 0), edge=edge)
            if ds:
                self._draw_dragon_fin(win, p, ds)
                self._draw_dragon_head(win, p, ds)

        self._draw_hud(win, font, big, state)
        if state:
            self._draw_minimap(win, state)

        # cho / hoi sinh
        if me is not None and not me["alive"]:
            txt = f"BAN DA CHET  -  hoi sinh sau {me.get('respawn', 0):.1f}s"
            t = big.render(txt, True, (250, 90, 90))
            win.blit(t, (WIDTH // 2 - t.get_width() // 2, HEIGHT // 2 - 20))
        elif state is None:
            t = big.render("Dang cho du lieu tu server...", True, (230, 230, 230))
            win.blit(t, (WIDTH // 2 - t.get_width() // 2, HEIGHT // 2 - 20))

    def _draw_grid(self, win):
        step = 100
        x0 = -((self.cam.x) % step)
        y0 = -((self.cam.y) % step)
        for x in range(int(x0), WIDTH, step):
            pygame.draw.line(win, (38, 40, 50), (x, 0), (x, HEIGHT))
        for y in range(int(y0), HEIGHT, step):
            pygame.draw.line(win, (38, 40, 50), (0, y), (WIDTH, y))

    def _draw_map_border(self, win):
        mw, mh = (MAP_W, MAP_H)
        if self.state:
            mw, mh = self.state.get("map", (MAP_W, MAP_H))
        sx, sy = self.cam.to_screen(0, 0)
        ex, ey = self.cam.to_screen(mw, mh)
        pygame.draw.rect(win, (200, 80, 80),
                         pygame.Rect(int(sx), int(sy), int(ex - sx), int(ey - sy)), 3)

    def _draw_hud(self, win, font, big, state):
        # ---- bang xep hang (top 8) ---- #
        players = list(self.all_players())
        players.sort(key=lambda p: p.get("score", 0), reverse=True)
        top = players[:8]

        panel = pygame.Rect(WIDTH - 230, 14, 216, 40 + len(top) * 22 + 8)
        pygame.draw.rect(win, (40, 42, 52), panel, border_radius=8)
        pygame.draw.rect(win, (80, 82, 92), panel, 1, border_radius=8)
        win.blit(big.render("XEP HANG", True, (235, 235, 235)),
                 (panel.x + 12, panel.y + 8))
        for i, p in enumerate(top):
            mine = (p["id"] == self.pid)
            col = (127, 208, 255) if mine else ((90, 200, 120) if i == 0 else (200, 200, 210))
            name = p.get("name", "P%d" % p["id"])
            line = "%d. %s : %s" % (i + 1, name, fmt_num(p.get("score", 0)))
            win.blit(font.render(line, True, col), (panel.x + 12, panel.y + 40 + i * 22))

        # ---- thanh nang luong (goc duoi trai) ---- #
        me = self.me()
        energy = me["energy"] if me else ENERGY_MAX
        bar = pygame.Rect(24, HEIGHT - 40, 1040, 22)
        pygame.draw.rect(win, (45, 47, 57), bar, border_radius=6)
        fill = pygame.Rect(bar.x, bar.y, int(bar.w * energy / ENERGY_MAX), bar.h)
        col = (90, 200, 120) if energy > 25 else (230, 90, 90)
        pygame.draw.rect(win, col, fill, border_radius=6)
        pygame.draw.rect(win, (120, 122, 132), bar, 2, border_radius=6)
        win.blit(font.render(f"NANG LUONG {int(energy)}%", True, (240, 240, 240)),
                 (bar.x + 10, bar.y + 1))
        if me and me.get("can_buff"):
            bt = font.render("NHAN [E]: Hoi day nang luong (/2 dau ran)", True, (255, 217, 94))
            win.blit(bt, (bar.x + 250, bar.y + 1))

        # ---- huong dan ---- #
        hint = "Chuot / Mui ten / WASD: di chuyen  |  Chuot trai / Space: tang toc  |  [E]: hoi nang luong"
        win.blit(font.render(hint, True, (150, 152, 162)), (24, HEIGHT - 68))

    @staticmethod
    def _poly(cx, cy, r, sides, rot):
        pts = []
        for i in range(sides):
            a = rot + i * math.tau / sides
            pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
        return pts

    @staticmethod
    def _star_pts(cx, cy, rO, rI, points, rot):
        pts = []
        for i in range(points * 2):
            rad = rO if i % 2 == 0 else rI
            a = rot + i * math.pi / points
            pts.append((cx + math.cos(a) * rad, cy + math.sin(a) * rad))
        return pts

    def _ob_pts(self, cx, cy, r, shape):
        if shape == "circle" or shape == "spiral":
            return None
        if shape == "triangle":
            return self._poly(cx, cy, r * 1.12, 3, -math.pi / 2)
        if shape == "hexagon":
            return self._poly(cx, cy, r, 6, 0)
        if shape == "diamond":
            return self._poly(cx, cy, r * 1.18, 4, -math.pi / 2)
        if shape == "pentagon":
            return self._poly(cx, cy, r * 1.08, 5, -math.pi / 2)
        if shape == "octagon":
            return self._poly(cx, cy, r, 8, math.pi / 8)
        if shape == "star":
            return self._star_pts(cx, cy, r * 1.2, r * 0.52, 5, -math.pi / 2)
        return None

    def _draw_obstacle(self, win, wx, wy, size, kind="red", shape="square"):
        sx, sy = self.cam.to_screen(wx, wy)
        if sx < -(size + 40) or sx > WIDTH + size + 40 or sy < -(size + 40) or sy > HEIGHT + size + 40:
            return
        is_red = (kind == "red")
        r = size / 2
        fill = (74, 42, 42) if is_red else (31, 61, 42)
        edge = (226, 85, 85) if is_red else (54, 226, 122)
        txtcol = (255, 179, 179) if is_red else (182, 245, 207)
        pts = self._ob_pts(sx, sy, r, shape)
        if pts:
            pygame.draw.polygon(win, fill, pts)
        elif shape in ("circle", "spiral"):
            pygame.draw.circle(win, fill, (int(sx), int(sy)), int(r))
        else:
            rect = pygame.Rect(0, 0, int(r * 2), int(r * 2))
            rect.center = (int(sx), int(sy))
            pygame.draw.rect(win, fill, rect, border_radius=10)
        if pts:
            pygame.draw.polygon(win, edge, pts, 3)
        elif shape in ("circle", "spiral"):
            pygame.draw.circle(win, edge, (int(sx), int(sy)), int(r), 3)
        else:
            rect = pygame.Rect(0, 0, int(r * 2), int(r * 2))
            rect.center = (int(sx), int(sy))
            pygame.draw.rect(win, edge, rect, 3, border_radius=10)
        if shape == "spiral":
            scol = (255, 210, 120) if is_red else (150, 255, 190)
            steps = 60
            prev = None
            for i in range(steps + 1):
                t = i / steps
                ang = t * 3.5 * math.tau
                rad = t * r * 0.85
                px, py = sx + math.cos(ang) * rad, sy + math.sin(ang) * rad
                if prev:
                    pygame.draw.line(win, scol, prev, (px, py), 3)
                prev = (px, py)
        f = pygame.font.SysFont("consolas", 13, bold=True)
        t = f.render("KE XAU", True, txtcol)
        win.blit(t, t.get_rect(center=(int(sx), int(sy))))

    _PU_STYLE = {
        "x2": ((35, 196, 106), (255, 255, 255)),
        "x4": ((47, 143, 214), (255, 255, 255)),
        "/2": ((226, 138, 54), (40, 30, 20)),
        "/4": ((226, 85, 85), (60, 20, 20)),
    }

    def _draw_powerup(self, win, wx, wy, kind, remain):
        sx, sy = self.cam.to_screen(wx, wy)
        if sx < -CUBE or sx > WIDTH + CUBE or sy < -CUBE or sy > HEIGHT + CUBE:
            return
        col, tcol = self._PU_STYLE.get(kind, ((123, 61, 255), (255, 255, 255)))
        alpha = max(0.25, min(1.0, remain / 1.5))
        r = pygame.Rect(0, 0, int(CUBE * 0.9), int(CUBE * 0.9))
        r.center = (int(sx), int(sy))
        if alpha < 1.0:
            surf = pygame.Surface((r.w + 6, r.h + 6), pygame.SRCALPHA)
            rr = pygame.Rect(3, 3, r.w, r.h)
            pygame.draw.rect(surf, (*col, int(255 * alpha)), rr, border_radius=8)
            pygame.draw.rect(surf, (*tcol, int(255 * alpha)), rr, 2, border_radius=8)
            win.blit(surf, (r.x - 3, r.y - 3))
        else:
            pygame.draw.rect(win, col, r, border_radius=8)
            pygame.draw.rect(win, tcol, r, 2, border_radius=8)
        f = pygame.font.SysFont("consolas", 15, bold=True)
        t = f.render(kind, True, tcol)
        win.blit(t, t.get_rect(center=r.center))

    def _draw_name(self, win, p):
        pass

    def _draw_dragon_head(self, win, p, ds):
        cubes = p.get("cubes")
        if not cubes:
            return
        hx, hy, _ = cubes[0]
        sx, sy = self.cam.to_screen(hx, hy)
        if sx < -CUBE * 3 or sx > WIDTH + CUBE * 3 or sy < -CUBE * 3 or sy > HEIGHT + CUBE * 3:
            return
        dx, dy = 0.0, -1.0
        if len(cubes) > 1:
            dx = cubes[0][0] - cubes[1][0]
            dy = cubes[0][1] - cubes[1][1]
            d = math.hypot(dx, dy)
            if d > 0.1:
                dx, dy = dx / d, dy / d
            else:
                dx, dy = 0.0, -1.0
        px, py = -dy, dx
        bx, by = -dx, -dy
        hc = ds["horn"]
        ec = ds["eye"]
        ac = ds["aura"]
        sz = int(CUBE * 4)
        aura = pygame.Surface((sz, sz), pygame.SRCALPHA)
        acx = sz // 2
        for r, a in [(int(CUBE * 1.5), 18), (int(CUBE * 1.0), 28), (int(CUBE * 0.6), 48)]:
            pygame.draw.circle(aura, (*ac, a), (acx, acx), r)
        win.blit(aura, (int(sx - acx), int(sy - acx)))
        ht = ds["horn_type"]
        for s in (-1, 1):
            bX, bY = sx + px * s * CUBE * 0.34, sy + py * s * CUBE * 0.34
            if ht == "spike":
                tX = bX + bx * CUBE * 0.7 + px * s * CUBE * 0.15
                tY = bY + by * CUBE * 0.7 + py * s * CUBE * 0.15
                pygame.draw.line(win, hc, (bX, bY), (tX, tY), 5)
                pygame.draw.circle(win, hc, (int(tX), int(tY)), 3)
            elif ht == "twist":
                pts = []
                for j in range(7):
                    f = j / 6
                    mx = bX + bx * CUBE * 0.7 * f + px * s * CUBE * 0.25 * math.sin(j * 1.8)
                    my = bY + by * CUBE * 0.7 * f + py * s * CUBE * 0.25 * math.sin(j * 1.8)
                    pts.append((mx, my))
                if len(pts) >= 2:
                    pygame.draw.lines(win, hc, False, pts, 4)
            else:
                pts = []
                for j in range(8):
                    f = j / 7
                    mx = bX + bx * CUBE * 0.65 * f + px * s * CUBE * (0.3 - 0.18 * f)
                    my = bY + by * CUBE * 0.65 * f + py * s * CUBE * (0.3 - 0.18 * f)
                    pts.append((mx, my))
                if len(pts) >= 2:
                    pygame.draw.lines(win, hc, False, pts, 4)
        for s in (-1, 1):
            eX = sx + dx * CUBE * 0.18 + px * s * CUBE * 0.2
            eY = sy + dy * CUBE * 0.18 + py * s * CUBE * 0.2
            pygame.draw.circle(win, ec, (int(eX), int(eY)), 3)
        ux, uy = -dy, dx
        for i in range(3):
            f = (i - 1) * 0.22
            baseX = sx + bx * CUBE * (0.15 + abs(f) * 0.5) + px * f * CUBE * 0.8
            baseY = sy + by * CUBE * (0.15 + abs(f) * 0.5) + py * f * CUBE * 0.8
            h = CUBE * (0.42 - abs(f) * 0.12)
            tx = baseX + ux * h
            ty = baseY + uy * h
            w1 = (baseX + px * 5, baseY + py * 5)
            w2 = (baseX - px * 5, baseY - py * 5)
            pygame.draw.polygon(win, hc, [w1, w2, (tx, ty)])

    def _draw_dragon_fin(self, win, p, ds):
        cubes = p.get("cubes")
        if not cubes or len(cubes) < 2:
            return
        t = pygame.time.get_ticks() / 400.0
        fc = ds["fin"]
        for i in range(len(cubes) - 1):
            cx, cy, _ = cubes[i]
            nx, ny, _ = cubes[i + 1]
            sx, sy = self.cam.to_screen(cx, cy)
            if sx < -CUBE or sx > WIDTH + CUBE or sy < -CUBE or sy > HEIGHT + CUBE:
                continue
            ddx, ddy = nx - cx, ny - cy
            d = math.hypot(ddx, ddy) or 1
            ux, uy = -ddy / d, ddx / d
            wave = math.sin(t + i * 0.5) * 0.15 + 1
            h = CUBE * 0.4 * wave
            p1 = (sx + ux * 5, sy + uy * 5)
            p2 = (sx - ux * 5, sy - uy * 5)
            p3 = (sx - uy * h, sy + ux * h)
            pygame.draw.polygon(win, fc, [p1, p2, p3])

    def _draw_minimap(self, win, state):
        sz = 150
        ox, oy = WIDTH - sz - 14, HEIGHT - sz - 40
        mw, mh = state.get("map", (MAP_W, MAP_H))
        sx = sz / mw
        sy = sz / mh
        panel = pygame.Rect(ox, oy, sz, sz)
        pygame.draw.rect(win, (30, 32, 42), panel, border_radius=6)
        pygame.draw.rect(win, (90, 92, 102), panel, 1, border_radius=6)
        for p in self.all_players():
            if not p.get("cubes"):
                continue
            hx, hy, _ = p["cubes"][0]
            col = (255, 255, 255) if p["id"] == self.pid else player_edge(p["id"])
            pygame.draw.circle(win, col,
                               (int(ox + hx * sx), int(oy + hy * sy)),
                               4 if p["id"] == self.pid else 3)

    def _show_disconnected(self, win, big):
        win.fill((24, 26, 34))
        t = big.render("MAT KET NOI VOI SERVER", True, (240, 90, 90))
        win.blit(t, (WIDTH // 2 - t.get_width() // 2, HEIGHT // 2 - 40))
        h = big.render("Nhan phim bat ky de thoat...", True, (220, 220, 220))
        win.blit(h, (WIDTH // 2 - h.get_width() // 2, HEIGHT // 2 + 10))
        pygame.display.flip()
        waiting = True
        while waiting:
            for e in pygame.event.get():
                if e.type in (pygame.QUIT, pygame.KEYDOWN):
                    waiting = False
        try:
            self.sock.close()
        except Exception:
            pass


# =============================== MAIN ================================== #
def main():
    pygame.init()
    win = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Cubes 2048 - Client")
    clock = pygame.time.Clock()

    sock, pid = connect_screen(win, clock)
    Game(sock, pid).loop(win, clock)
    pygame.quit()


if __name__ == "__main__":
    main()
