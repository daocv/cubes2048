"""
game_core.py  -  Logic game thu tung cua "Cubes 2048".
Tat ca server (server.py / server_web.py / server_cloud.py) dung chung module nay.

Tinh nang:
  - Nhieu nguoi choi (co dat ten) + 3 bot AI cua he thong.
  - Ban do lon, nhieu khoi an (luoi khong gian).
  - Vat can "KE XAU": xanh = chan duong (khong chet), do = chet.
  - O suc manh: x2 / x4 / /2 / /4  (random, bien mat sau 5 giay).
  - Dau cham dau: cung gia tri -> khong chet.
  - Dong goi co "cull" theo khung nhin nguoi xem.
"""

import math
import random
from collections import deque

# ============================== HE SO GAME ============================== #
MAP_W, MAP_H = 9000, 9000
CUBE = 40
SPACING = 40
NORMAL_SPEED = 170
BOOST_SPEED = 300
FOOD_COUNT = 1500
FOOD_CAP = 1500

OBSTACLE_COUNT = 10
GREEN_COUNT = 6          # chan duong (khong chet)
RED_COUNT = 4            # chet
OBSTACLE_SIZE = 120
OBSTACLE_NAME = "KE XAU"
OBSTACLE_SHAPES = ["square", "circle", "triangle", "hexagon", "diamond",
                   "pentagon", "star", "octagon", "spiral"]

BUFF_THRESHOLD = 1_000_000
DEATH_FOOD_LIFE = 3.0

POWERUP_COUNT = 8
POWERUP_LIFE = 5.0       # giay
PU_KINDS = ["x2", "x4", "/2", "/4"]
PU_WEIGHTS = [40, 12, 30, 18]

BOT_COUNT = 3
BOT_NAMES = ["HocNgu", "LuoiBieng", "HonLao"]
HUNTER_NAMES = ["ChuaTe", "MaDoc", "SatThu"]
HUNTER_SPEED_MULT = 0.8
BOT_SPEED_MULT = 2.0
POLICE_INTERVAL = 180.0
POLICE_MAX = 5
POLICE_SPEED_MULT = 0.6

ENERGY_MAX = 100.0
ENERGY_DRAIN = 45.0
ENERGY_REGEN = 25.0
MYSTERY_INTERVAL = 300.0
MYSTERY_LIFE = 30.0
MYSTERY_ENERGY_TIME = 30.0
TICK = 1.0 / 60.0
VIEW_HALF_W = 720
VIEW_HALF_H = 540
MAX_NAME = 12
GRID_CELL = 160
MAX_CUBES = 40


def clamp(v, lo, hi):
    return lo if v < lo else (hi if v > hi else v)


# =============================== CON RAN ================================ #
class Snake:
    def __init__(self, pid, x, y, value=2, name=None, is_bot=False, speed_mult=1.0):
        self.pid = pid
        self.name = (name or f"P{pid}")[:MAX_NAME]
        self.is_bot = is_bot
        self.speed_mult = speed_mult
        self.cubes = [{"x": float(x), "y": float(y), "value": value}]
        self.path = deque()
        self.path.append((float(x), float(y)))
        self.energy = ENERGY_MAX
        self.alive = True
        self.respawn = 0.0
        self.boost = False
        self.target = (float(x), float(y))
        self.energy_buff_used = False
        self.energy_lock = 0.0

    @property
    def head(self):
        return self.cubes[0]

    @property
    def score(self):
        return sum(c["value"] for c in self.cubes)

    @property
    def length(self):
        return len(self.cubes)

    def set_target(self, x, y):
        self.target = (float(x), float(y))

    def die(self):
        self.alive = False
        self.respawn = 3.0
        scattered = [(c["x"], c["y"], c["value"]) for c in self.cubes]
        self.cubes = []
        return scattered

    def respawn_at(self, x, y):
        self.cubes = [{"x": float(x), "y": float(y), "value": 2}]
        self.path = deque()
        self.path.append((float(x), float(y)))
        self.energy = ENERGY_MAX
        self.alive = True
        self.respawn = 0.0
        self.energy_buff_used = False
        self.energy_lock = 0.0

    def update(self, dt, boost):
        if not self.alive:
            return
        head = self.cubes[0]
        dx = self.target[0] - head["x"]
        dy = self.target[1] - head["y"]
        dist = math.hypot(dx, dy)
        if dist > 1.0:
            vx, vy = dx / dist, dy / dist
        else:
            vx = vy = 0.0

        if self.energy_lock > 0:
            self.energy_lock = max(0.0, self.energy_lock - dt)
            self.energy = ENERGY_MAX
            self.boost = True
        elif boost and self.energy > 0:
            self.energy = max(0.0, self.energy - ENERGY_DRAIN * dt)
            self.boost = True
        else:
            self.energy = min(ENERGY_MAX, self.energy + ENERGY_REGEN * dt)
            self.boost = False
        speed = (BOOST_SPEED if self.boost else NORMAL_SPEED) * self.speed_mult

        head["x"] = clamp(head["x"] + vx * speed * dt, CUBE, MAP_W - CUBE)
        head["y"] = clamp(head["y"] + vy * speed * dt, CUBE, MAP_H - CUBE)

        self.path.appendleft((head["x"], head["y"]))
        self._trim_path()
        for i in range(1, len(self.cubes)):
            px, py = self._point_at(i * SPACING)
            self.cubes[i]["x"] = px
            self.cubes[i]["y"] = py

    def _trim_path(self):
        need = max(len(self.cubes) - 1, 0) * SPACING + 250
        acc = 0.0
        keep = 1
        prev = self.path[0]
        for i in range(1, len(self.path)):
            cur = self.path[i]
            acc += math.hypot(cur[0] - prev[0], cur[1] - prev[1])
            prev = cur
            keep = i + 1
            if acc >= need:
                break
        while len(self.path) > keep:
            self.path.pop()

    def _point_at(self, dist):
        if len(self.path) < 2:
            return self.path[0]
        acc = 0.0
        prev = self.path[0]
        for i in range(1, len(self.path)):
            cur = self.path[i]
            seg = math.hypot(cur[0] - prev[0], cur[1] - prev[1])
            if acc + seg >= dist:
                if seg == 0:
                    return prev
                t = (dist - acc) / seg
                return (prev[0] + (cur[0] - prev[0]) * t,
                        prev[1] + (cur[1] - prev[1]) * t)
            acc += seg
            prev = cur
        return self.path[-1]


# ============================ THE GIOI GAME ============================= #
class GameWorld:
    def __init__(self):
        self.players = {}
        self.inputs = {}
        self.foods = []
        self.powerups = []      # [{x, y, kind, born}]
        self.obstacles = []     # [{x, y, size, kind}]
        self.bots = set()
        self.hunter_bots = set()
        self.next_pid = 1
        self.time = 0.0
        self.mystery_box = None
        self.mystery_timer = 0.0
        self.police_timer = 0.0
        self.police_bots = {}
        self._gen_obstacles()
        self._spawn_bots()

    # ---------- quan ly nguoi choi ---------- #
    def add_player(self, name=None, is_bot=False, speed_mult=1.0):
        pid = self.next_pid
        self.next_pid += 1
        x = random.uniform(500, MAP_W - 500)
        y = random.uniform(500, MAP_H - 500)
        self.players[pid] = Snake(pid, x, y, name=name, is_bot=is_bot, speed_mult=speed_mult)
        self.inputs[pid] = (x, y, False)
        return pid

    def set_name(self, pid, name):
        s = self.players.get(pid)
        if s and name:
            nm = str(name).strip()[:MAX_NAME]
            existing = {p.name for p in self.players.values() if p.pid != pid}
            if nm.upper() in {e.upper() for e in existing}:
                base = nm
                i = 2
                while (base + str(i))[:MAX_NAME].upper() in {e.upper() for e in existing}:
                    i += 1
                nm = (base + str(i))[:MAX_NAME]
            s.name = nm

    def remove_player(self, pid):
        self.players.pop(pid, None)
        self.inputs.pop(pid, None)

    def set_input(self, pid, mx, my, boost):
        self.inputs[pid] = (float(mx), float(my), bool(boost))

    def sacrifice(self, pid):
        s = self.players.get(pid)
        if not s or not s.alive or s.energy_buff_used:
            return False
        if not s.cubes or s.cubes[0]["value"] < BUFF_THRESHOLD:
            return False
        s.cubes[0]["value"] = max(2, s.cubes[0]["value"] // 2)
        s.energy = ENERGY_MAX
        s.energy_buff_used = True
        return True

    # ---------- khoi tao vat can / bot ---------- #
    def _gen_obstacles(self):
        self.obstacles = []
        kinds = (["green"] * GREEN_COUNT) + (["red"] * RED_COUNT)
        random.shuffle(kinds)
        for k in kinds:
            self.obstacles.append({
                "x": random.uniform(400, MAP_W - 400),
                "y": random.uniform(400, MAP_H - 400),
                "size": OBSTACLE_SIZE + random.uniform(-20, 40),
                "kind": k,
                "shape": random.choice(OBSTACLE_SHAPES),
            })

    def _spawn_bots(self):
        for nm in BOT_NAMES[:BOT_COUNT]:
            self.bots.add(self.add_player(nm, is_bot=True, speed_mult=BOT_SPEED_MULT))
        for nm in HUNTER_NAMES:
            self.hunter_bots.add(self.add_player(nm, is_bot=True, speed_mult=HUNTER_SPEED_MULT))
        self.bots |= self.hunter_bots

    def _bot_target(self, s):
        h = s.head
        # tranh vat can do gan day
        for ob in self.obstacles:
            if ob["kind"] != "red":
                continue
            if abs(h["x"] - ob["x"]) < ob["size"] and abs(h["y"] - ob["y"]) < ob["size"]:
                return (h["x"] - (ob["x"] - h["x"]) * 2,
                        h["y"] - (ob["y"] - h["y"]) * 2)
        # tranh bien
        if h["x"] < 500 or h["x"] > MAP_W - 500 or h["y"] < 500 or h["y"] > MAP_H - 500:
            return (MAP_W / 2 + random.uniform(-600, 600),
                    MAP_H / 2 + random.uniform(-600, 600))
        # duoi khoi an gan nhat (lay mau)
        sample = random.sample(self.foods, min(90, len(self.foods)))
        best = min(sample, key=lambda f: (f["x"] - h["x"]) ** 2 + (f["y"] - h["y"]) ** 2)
        return (best["x"] + random.uniform(-30, 30), best["y"] + random.uniform(-30, 30))

    def _update_bot_speed(self):
        _, max_val = self._highest_player()
        scale = 4 if max_val >= 1_000_000_000 else (2 if max_val >= 1_000_000 else 1)
        for pid in self.bots:
            s = self.players.get(pid)
            if s:
                base = POLICE_SPEED_MULT if pid in self.police_bots else (HUNTER_SPEED_MULT if pid in self.hunter_bots else BOT_SPEED_MULT)
                s.speed_mult = base * scale

    def _update_bots(self):
        for pid in self.bots:
            if pid in self.police_bots or pid in self.hunter_bots:
                continue
            s = self.players.get(pid)
            if s and s.alive and s.cubes:
                tx, ty = self._bot_target(s)
                boost = s.energy > 55 and random.random() < 0.35
                self.inputs[pid] = (tx, ty, boost)

    def _hunter_target(self, s):
        """Tim nguoi choi gan nhat de tan cong."""
        h = s.head
        # tranh bien
        if h["x"] < 400 or h["x"] > MAP_W - 400 or h["y"] < 400 or h["y"] > MAP_H - 400:
            return (MAP_W / 2 + random.uniform(-600, 600),
                    MAP_H / 2 + random.uniform(-600, 600)), False
        best_pid, best_d2 = None, float("inf")
        for tp, ts in self.players.items():
            if tp == s.pid or ts.is_bot or not ts.alive or not ts.cubes:
                continue
            th = ts.head
            d2 = (th["x"] - h["x"]) ** 2 + (th["y"] - h["y"]) ** 2
            if d2 < best_d2:
                best_d2, best_pid = d2, tp
        if best_pid is None:
            # khong co nguoi choi, di an food
            return self._bot_target(s), False
        tgt = self.players[best_pid]
        th = tgt.head
        # du doan vi tri nguoi choi (cat duong)
        if len(tgt.cubes) > 1:
            vx = tgt.cubes[0]["x"] - tgt.cubes[1]["x"]
            vy = tgt.cubes[0]["y"] - tgt.cubes[1]["y"]
            lead = min(40, best_d2 ** 0.5 * 0.15)
            px = th["x"] + vx * lead
            py = th["y"] + vy * lead
        else:
            px, py = th["x"], th["y"]
        return (px, py), best_d2 < 450 ** 2

    def _update_hunters(self):
        for pid in self.hunter_bots:
            s = self.players.get(pid)
            if not s or not s.alive or not s.cubes:
                continue
            (tx, ty), close = self._hunter_target(s)
            boost = close and s.energy > 25 or (s.energy > 60 and random.random() < 0.4)
            self.inputs[pid] = (tx, ty, boost)

    def _highest_player(self):
        best_pid, best_val = None, 0
        for pid, s in self.players.items():
            if s.alive and s.cubes and not s.is_bot:
                v = s.cubes[0]["value"]
                if v > best_val:
                    best_val, best_pid = v, pid
        return best_pid, best_val

    def _update_police(self, dt):
        tgt_pid, tgt_val = self._highest_player()
        if tgt_pid is None or tgt_val < BUFF_THRESHOLD:
            self.police_timer = 0.0
            return
        self.police_timer += dt
        if self.police_timer >= POLICE_INTERVAL and len(self.police_bots) < POLICE_MAX:
            self.police_timer = 0.0
            self._spawn_police(tgt_pid, tgt_val)
        for pid in list(self.police_bots):
            bot = self.players.get(pid)
            if not bot or not bot.alive or not bot.cubes:
                continue
            tgt = self.players.get(tgt_pid)
            if tgt and tgt.alive and tgt.cubes:
                h = tgt.cubes[0]
                self.inputs[pid] = (h["x"], h["y"], True)
            else:
                npid, _ = self._highest_player()
                if npid:
                    h = self.players[npid].cubes[0]
                    self.inputs[pid] = (h["x"], h["y"], True)

    def _spawn_police(self, target_pid, target_val):
        tgt = self.players.get(target_pid)
        if not tgt or not tgt.cubes:
            return
        h = tgt.cubes[0]
        ang = random.uniform(0, math.pi * 2)
        dist = random.uniform(1200, 1800)
        px = clamp(h["x"] + math.cos(ang) * dist, 200, MAP_W - 200)
        py = clamp(h["y"] + math.sin(ang) * dist, 200, MAP_H - 200)
        idx = len(self.police_bots) + 1
        name = ("CANHSAT%d" % idx)[:MAX_NAME]
        pid = self.next_pid
        self.next_pid += 1
        bot = Snake(pid, px, py, value=max(2, target_val * 2), name=name,
                    is_bot=True, speed_mult=POLICE_SPEED_MULT)
        self.players[pid] = bot
        self.inputs[pid] = (h["x"], h["y"], True)
        self.bots.add(pid)
        self.police_bots[pid] = True

    # ---------- buoc tinh toan ---------- #
    def step(self, dt):
        self.time += dt
        while len(self.foods) < FOOD_COUNT:
            self.foods.append(self._rand_food())
        while len(self.powerups) < POWERUP_COUNT:
            self.powerups.append(self._rand_powerup())
        # power-up het han
        self.powerups = [p for p in self.powerups
                         if self.time - p["born"] < POWERUP_LIFE]
        # death food het han
        self.foods = [f for f in self.foods
                      if "expire" not in f or self.time < f["expire"]]

        self._update_bot_speed()
        self._update_bots()
        self._update_hunters()
        self._update_mystery(dt)
        self._update_police(dt)

        for pid, snake in self.players.items():
            if not snake.alive:
                snake.respawn -= dt
                if snake.respawn <= 0:
                    snake.respawn_at(random.uniform(300, MAP_W - 300),
                                     random.uniform(300, MAP_H - 300))
                    if pid in self.police_bots:
                        mx = max((s.cubes[0]["value"] for s in self.players.values()
                                  if s.alive and s.cubes and not s.is_bot), default=2)
                        snake.cubes[0]["value"] = max(2, mx * 2)
                continue
            inp = self.inputs.get(pid)
            if inp:
                snake.set_target(inp[0], inp[1])
                snake.update(dt, inp[2])
            else:
                snake.update(dt, False)
            self._resolve_greens(snake)     # vat can xanh: chan dau

        self._handle_food()
        self._handle_powerups()
        for snake in self.players.values():
            self._merge(snake)
            self._enforce_cube_cap(snake)
        self._handle_red_obstacles()
        self._handle_collisions()

        if len(self.foods) > FOOD_CAP:
            self.foods = self.foods[:FOOD_CAP]

    def _update_mystery(self, dt):
        if self.mystery_box is None:
            self.mystery_timer += dt
            if self.mystery_timer >= MYSTERY_INTERVAL:
                self.mystery_timer = 0.0
                self.mystery_box = {
                    "x": random.uniform(500, MAP_W - 500),
                    "y": random.uniform(500, MAP_H - 500),
                    "born": self.time,
                }
            return
        if self.time - self.mystery_box["born"] > MYSTERY_LIFE:
            self.mystery_box = None
            return
        for snake in self.players.values():
            if not snake.alive or not snake.cubes:
                continue
            h = snake.cubes[0]
            if (abs(h["x"] - self.mystery_box["x"]) < CUBE * 0.9 and
                    abs(h["y"] - self.mystery_box["y"]) < CUBE * 0.9):
                good = random.random() < 0.6
                for c in snake.cubes:
                    if good:
                        c["value"] = max(2, c["value"] * 16)
                    else:
                        c["value"] = max(2, c["value"] // 16)
                snake.energy = ENERGY_MAX
                snake.energy_lock = MYSTERY_ENERGY_TIME
                self.mystery_box = None
                break

    def _rand_food(self):
        val = random.choices([2, 4, 8, 16], weights=[90, 5, 3, 2])[0]
        return {"x": random.uniform(50, MAP_W - 50),
                "y": random.uniform(50, MAP_H - 50), "value": val}

    def _rand_powerup(self):
        kind = random.choices(PU_KINDS, weights=PU_WEIGHTS)[0]
        return {"x": random.uniform(200, MAP_W - 200),
                "y": random.uniform(200, MAP_H - 200),
                "kind": kind, "born": self.time}

    # ---------- vat can xanh: day dau ra ---------- #
    def _resolve_greens(self, snake):
        if not snake.alive or not snake.cubes:
            return
        h = snake.head
        for _ in range(2):
            for ob in self.obstacles:
                if ob["kind"] != "green":
                    continue
                half = ob["size"] / 2 + CUBE * 0.4
                dx = h["x"] - ob["x"]
                dy = h["y"] - ob["y"]
                ox = half - abs(dx)
                oy = half - abs(dy)
                if ox > 0 and oy > 0:
                    if ox < oy:
                        h["x"] = ob["x"] + (half if dx >= 0 else -half)
                    else:
                        h["y"] = ob["y"] + (half if dy >= 0 else -half)
        h["x"] = clamp(h["x"], CUBE, MAP_W - CUBE)
        h["y"] = clamp(h["y"], CUBE, MAP_H - CUBE)

    # ---------- an khoi ---------- #
    def _handle_food(self):
        grid = {}
        for fi, f in enumerate(self.foods):
            key = (int(f["x"] // GRID_CELL), int(f["y"] // GRID_CELL))
            grid.setdefault(key, []).append(fi)
        eaten = set()
        for snake in self.players.values():
            if not snake.alive:
                continue
            for cube in snake.cubes:
                cx = int(cube["x"] // GRID_CELL)
                cy = int(cube["y"] // GRID_CELL)
                for gx in (cx - 1, cx, cx + 1):
                    for gy in (cy - 1, cy, cy + 1):
                        for fi in grid.get((gx, gy), ()):
                            if fi in eaten:
                                continue
                            f = self.foods[fi]
                            if (abs(cube["x"] - f["x"]) < CUBE * 0.8 and
                                    abs(cube["y"] - f["y"]) < CUBE * 0.8):
                                snake.cubes.append({"x": cube["x"], "y": cube["y"],
                                                    "value": f["value"]})
                                eaten.add(fi)
        if eaten:
            self.foods = [f for i, f in enumerate(self.foods) if i not in eaten]

    def _handle_powerups(self):
        for snake in self.players.values():
            if not snake.alive or not snake.cubes:
                continue
            h = snake.cubes[0]
            for p in list(self.powerups):
                if abs(h["x"] - p["x"]) < CUBE * 0.8 and abs(h["y"] - p["y"]) < CUBE * 0.8:
                    self._apply_powerup(snake, p["kind"])
                    self.powerups.remove(p)
                    break

    def _apply_powerup(self, snake, kind):
        if not snake.cubes:
            return
        for c in snake.cubes:
            v = c["value"]
            if kind == "x2":
                v *= 2
            elif kind == "x4":
                v *= 4
            elif kind == "/2":
                v = max(2, v // 2)
            elif kind == "/4":
                v = max(2, v // 4)
            c["value"] = v

    def _merge(self, snake):
        if not snake.alive or not snake.cubes:
            return
        vals = sorted((c["value"] for c in snake.cubes), reverse=True)
        while True:
            out = []
            for v in vals:
                if out and out[-1] == v:
                    out[-1] *= 2
                else:
                    out.append(v)
            if len(out) == len(vals):
                break
            vals = sorted(out, reverse=True)
        for i in range(len(vals)):
            snake.cubes[i]["value"] = vals[i]
        del snake.cubes[len(vals):]

    def _enforce_cube_cap(self, snake):
        if not snake.cubes or len(snake.cubes) <= MAX_CUBES:
            return
        excess = snake.cubes[MAX_CUBES:]
        snake.cubes[MAX_CUBES - 1]["value"] += sum(c["value"] for c in excess)
        del snake.cubes[MAX_CUBES:]

    def _handle_red_obstacles(self):
        for snake in self.players.values():
            if not snake.alive or not snake.cubes:
                continue
            h = snake.cubes[0]
            for ob in self.obstacles:
                if ob["kind"] != "red":
                    continue
                if (abs(h["x"] - ob["x"]) < ob["size"] / 2 and
                        abs(h["y"] - ob["y"]) < ob["size"] / 2):
                    self._kill(snake)
                    break

    def _handle_collisions(self):
        grid = {}
        for pid, s in self.players.items():
            if not s.alive or not s.cubes:
                continue
            for idx, c in enumerate(s.cubes):
                key = (int(c["x"] // GRID_CELL), int(c["y"] // GRID_CELL))
                grid.setdefault(key, []).append((pid, idx))

        for apid, attacker in list(self.players.items()):
            if not attacker.alive or not attacker.cubes:
                continue
            h = attacker.cubes[0]
            hv = h["value"]
            cgx, cgy = int(h["x"] // GRID_CELL), int(h["y"] // GRID_CELL)
            done = False
            for gx in (cgx - 1, cgx, cgx + 1):
                if done:
                    break
                for gy in (cgy - 1, cgy, cgy + 1):
                    if done:
                        break
                    for (bpid, bidx) in grid.get((gx, gy), ()):
                        if bpid == apid:
                            continue
                        defender = self.players.get(bpid)
                        if not defender or not defender.alive or bidx >= len(defender.cubes):
                            continue
                        bc = defender.cubes[bidx]
                        if abs(h["x"] - bc["x"]) >= CUBE * 0.7 or abs(h["y"] - bc["y"]) >= CUBE * 0.7:
                            continue
                        if bidx == 0:
                            if hv > bc["value"]:
                                self._kill(defender)
                            elif hv < bc["value"]:
                                self._kill(attacker)
                        elif hv >= bc["value"]:
                            bitten = defender.cubes[bidx:]
                            defender.cubes = defender.cubes[:bidx]
                            if not defender.cubes:
                                self._kill(defender)
                            else:
                                attacker.cubes.append({"x": h["x"], "y": h["y"],
                                                       "value": bitten[0]["value"]})
                            for c in bitten[1:]:
                                self.foods.append({"x": c["x"] + random.uniform(-25, 25),
                                                   "y": c["y"] + random.uniform(-25, 25),
                                                   "value": c["value"],
                                                   "expire": self.time + DEATH_FOOD_LIFE})
                        else:
                            self._kill(attacker)
                        done = True
                        break

    def _kill(self, snake):
        if not snake.alive:
            return
        for x, y, v in snake.die():
            self.foods.append({"x": clamp(x + random.uniform(-30, 30), 30, MAP_W - 30),
                               "y": clamp(y + random.uniform(-30, 30), 30, MAP_H - 30),
                               "value": v, "expire": self.time + DEATH_FOOD_LIFE})

    # ---------- dong goi trang thai ---------- #
    def serialize(self, viewer_pid=None):
        vx = vy = None
        if viewer_pid is not None and viewer_pid in self.players:
            s = self.players[viewer_pid]
            if s.cubes:
                vx, vy = s.head["x"], s.head["y"]

        def near(x, y):
            if vx is None:
                return True
            return abs(x - vx) <= VIEW_HALF_W and abs(y - vy) <= VIEW_HALF_H

        players = [{
            "id": pid, "name": s.name, "bot": s.is_bot, "alive": s.alive,
            "energy": round(s.energy, 1), "respawn": round(s.respawn, 1),
            "score": s.score, "length": s.length,
            "police": pid in self.police_bots,
            "energy_lock": round(s.energy_lock, 1),
            "cubes": [[round(c["x"], 1), round(c["y"], 1), c["value"]] for c in s.cubes],
            "can_buff": (s.alive and bool(s.cubes) and
                         s.cubes[0]["value"] >= BUFF_THRESHOLD and
                         not s.energy_buff_used),
            "buff_used": s.energy_buff_used,
        } for pid, s in self.players.items()]

        foods = []
        for f in self.foods:
            if not near(f["x"], f["y"]):
                continue
            item = [round(f["x"], 1), round(f["y"], 1), f["value"]]
            if "expire" in f:
                item.append(round(max(0, f["expire"] - self.time), 1))
            foods.append(item)
        powerups = [[round(p["x"], 1), round(p["y"], 1), p["kind"],
                     round(POWERUP_LIFE - (self.time - p["born"]), 1)]
                    for p in self.powerups]
        obstacles = [[round(o["x"], 1), round(o["y"], 1), round(o["size"], 1),
                      o["kind"], o["shape"]]
                     for o in self.obstacles]

        mystery = None
        if self.mystery_box is not None:
            mystery = [round(self.mystery_box["x"], 1), round(self.mystery_box["y"], 1),
                       round(max(0, MYSTERY_LIFE - (self.time - self.mystery_box["born"])), 1), 0]
        else:
            cd = max(0, MYSTERY_INTERVAL - self.mystery_timer)
            mystery = [-1, -1, 0, round(cd, 1)]

        return {
            "players": players,
            "foods": foods,
            "powerups": powerups,
            "obstacles": obstacles,
            "mystery": mystery,
            "map": [MAP_W, MAP_H],
        }
