"use strict";
// game_core.js - Logic game "Thu thach cung Minh Dat" (Node.js version)

// ============================== HE SO GAME ============================== //
const MAP_W = 9000, MAP_H = 9000;
const CUBE = 40;
const SPACING = 40;
const NORMAL_SPEED = 170;
const BOOST_SPEED = 300;
const FOOD_COUNT = 1500;
const FOOD_CAP = 1500;

const OBSTACLE_COUNT = 10;
const GREEN_COUNT = 6;
const RED_COUNT = 4;
const OBSTACLE_SIZE = 120;
const OBSTACLE_NAME = "KE XAU";
const OBSTACLE_SHAPES = ["square","circle","triangle","hexagon","diamond","pentagon","star","octagon","spiral"];

const BUFF_THRESHOLD = 1000000;
const DEATH_FOOD_LIFE = 3.0;

const POWERUP_COUNT = 8;
const POWERUP_LIFE = 5.0;
const PU_KINDS = ["x2","x4","/2","/4"];
const PU_WEIGHTS = [40,12,30,18];

const BOT_COUNT = 3;
const BOT_NAMES = ["HocNgu","LuoiBieng","HonLao"];
const HUNTER_NAMES = ["ChuaTe","MaDoc","SatThu"];
const HUNTER_SPEED_MULT = 0.8;
const BOT_SPEED_MULT = 2.0;
const POLICE_INTERVAL = 180.0;
const POLICE_MAX = 5;
const POLICE_SPEED_MULT = 0.4;

const ENERGY_MAX = 100.0;
const ENERGY_DRAIN = 45.0;
const ENERGY_REGEN = 25.0;
const MYSTERY_INTERVAL = 300.0;
const MYSTERY_LIFE = 30.0;
const MYSTERY_ENERGY_TIME = 30.0;
const TICK = 1/60;
const VIEW_HALF_W = 720;
const VIEW_HALF_H = 540;
const MAX_NAME = 12;
const GRID_CELL = 160;
const MAX_CUBES = 25;

function clamp(v, lo, hi) { return v < lo ? lo : (v > hi ? hi : v); }
function rand(lo, hi) { return lo + Math.random() * (hi - lo); }
function randInt(lo, hi) { return Math.floor(rand(lo, hi + 1)); }
function choice(arr) { return arr[Math.floor(Math.random() * arr.length)]; }

function weightedChoice(items, weights) {
  let total = weights.reduce((a, b) => a + b, 0);
  let r = Math.random() * total;
  for (let i = 0; i < items.length; i++) {
    r -= weights[i];
    if (r <= 0) return items[i];
  }
  return items[items.length - 1];
}

// =============================== CON RAN ================================ //
class Snake {
  constructor(pid, x, y, value = 2, name = null, isBot = false, speedMult = 1.0) {
    this.pid = pid;
    this.name = (name || `P${pid}`).slice(0, MAX_NAME);
    this.isBot = isBot;
    this.speedMult = speedMult;
    this.cubes = [{ x: +x, y: +y, value }];
    this.path = [[+x, +y]];
    this.energy = ENERGY_MAX;
    this.alive = true;
    this.respawn = 0.0;
    this.boost = false;
    this.target = [+x, +y];
    this.energyBuffUsed = false;
    this.energyLock = 0.0;
  }

  get head() { return this.cubes[0]; }
  get score() { return this.cubes.reduce((s, c) => s + c.value, 0); }
  get length() { return this.cubes.length; }

  setTarget(x, y) { this.target = [+x, +y]; }

  die() {
    this.alive = false;
    this.respawn = 3.0;
    const scattered = this.cubes.map(c => [c.x, c.y, c.value]);
    this.cubes = [];
    return scattered;
  }

  respawnAt(x, y) {
    this.cubes = [{ x: +x, y: +y, value: 2 }];
    this.path = [[+x, +y]];
    this.energy = ENERGY_MAX;
    this.alive = true;
    this.respawn = 0.0;
    this.energyBuffUsed = false;
    this.energyLock = 0.0;
  }

  update(dt, boost) {
    if (!this.alive) return;
    const head = this.cubes[0];
    let dx = this.target[0] - head.x;
    let dy = this.target[1] - head.y;
    const dist = Math.hypot(dx, dy);
    let vx = 0, vy = 0;
    if (dist > 1.0) { vx = dx / dist; vy = dy / dist; }

    if (this.energyLock > 0) {
      this.energyLock = Math.max(0, this.energyLock - dt);
      this.energy = ENERGY_MAX;
      this.boost = true;
    } else if (boost && this.energy > 0) {
      this.energy = Math.max(0, this.energy - ENERGY_DRAIN * dt);
      this.boost = true;
    } else {
      this.energy = Math.min(ENERGY_MAX, this.energy + ENERGY_REGEN * dt);
      this.boost = false;
    }
    const speed = (this.boost ? BOOST_SPEED : NORMAL_SPEED) * this.speedMult;

    head.x = clamp(head.x + vx * speed * dt, CUBE, MAP_W - CUBE);
    head.y = clamp(head.y + vy * speed * dt, CUBE, MAP_H - CUBE);

    this.path.unshift([head.x, head.y]);
    this._trimPath();
    for (let i = 1; i < this.cubes.length; i++) {
      const [px, py] = this._pointAt(i * SPACING);
      this.cubes[i].x = px;
      this.cubes[i].y = py;
    }
  }

  _trimPath() {
    const need = Math.max(this.cubes.length - 1, 0) * SPACING + 250;
    let acc = 0;
    let keep = 1;
    for (let i = 1; i < this.path.length; i++) {
      acc += Math.hypot(this.path[i][0] - this.path[i - 1][0], this.path[i][1] - this.path[i - 1][1]);
      keep = i + 1;
      if (acc >= need) break;
    }
    if (this.path.length > keep) this.path.length = keep;
  }

  _pointAt(dist) {
    if (this.path.length < 2) return this.path[0];
    let acc = 0;
    for (let i = 1; i < this.path.length; i++) {
      const [px, py] = this.path[i - 1];
      const [cx, cy] = this.path[i];
      const seg = Math.hypot(cx - px, cy - py);
      if (acc + seg >= dist) {
        if (seg === 0) return [px, py];
        const t = (dist - acc) / seg;
        return [px + (cx - px) * t, py + (cy - py) * t];
      }
      acc += seg;
    }
    return this.path[this.path.length - 1];
  }
}

// ============================ THE GIOI GAME ============================= //
class GameWorld {
  constructor() {
    this.players = new Map();
    this.inputs = {};
    this.foods = [];
    this.powerups = [];
    this.obstacles = [];
    this.bots = new Set();
    this.hunterBots = new Set();
    this.policeBots = new Set();
    this.nextPid = 1;
    this.time = 0.0;
    this.mysteryBox = null;
    this.mysteryTimer = 0.0;
    this.policeTimer = 0.0;
    this._genObstacles();
    this._spawnBots();
  }

  // ---------- quan ly nguoi choi ---------- //
  addPlayer(name = null, isBot = false, speedMult = 1.0) {
    const pid = this.nextPid++;
    const x = rand(500, MAP_W - 500);
    const y = rand(500, MAP_H - 500);
    this.players.set(pid, new Snake(pid, x, y, 2, name, isBot, speedMult));
    this.inputs[pid] = [x, y, false];
    return pid;
  }

  setName(pid, name) {
    const s = this.players.get(pid);
    if (!s || !name) return;
    let nm = String(name).trim().slice(0, MAX_NAME);
    if (!nm) return;
    const existing = new Set();
    for (const [tp, ts] of this.players) {
      if (tp !== pid) existing.add(ts.name.toUpperCase());
    }
    if (existing.has(nm.toUpperCase())) {
      let base = nm, i = 2;
      while (existing.has((base + i).slice(0, MAX_NAME).toUpperCase())) i++;
      nm = (base + i).slice(0, MAX_NAME);
    }
    s.name = nm;
  }

  removePlayer(pid) {
    this.players.delete(pid);
    delete this.inputs[pid];
  }

  setInput(pid, mx, my, boost) {
    this.inputs[pid] = [+mx, +my, !!boost];
  }

  sacrifice(pid) {
    const s = this.players.get(pid);
    if (!s || !s.alive || s.energyBuffUsed) return false;
    if (!s.cubes || s.cubes[0].value < BUFF_THRESHOLD) return false;
    s.cubes[0].value = Math.max(2, Math.floor(s.cubes[0].value / 2));
    s.energy = ENERGY_MAX;
    s.energyBuffUsed = true;
    return true;
  }

  // ---------- khoi tao ---------- //
  _genObstacles() {
    this.obstacles = [];
    const kinds = Array(GREEN_COUNT).fill("green").concat(Array(RED_COUNT).fill("red"));
    for (let i = kinds.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [kinds[i], kinds[j]] = [kinds[j], kinds[i]];
    }
    for (const k of kinds) {
      this.obstacles.push({
        x: rand(400, MAP_W - 400),
        y: rand(400, MAP_H - 400),
        size: OBSTACLE_SIZE + rand(-20, 40),
        kind: k,
        shape: choice(OBSTACLE_SHAPES),
      });
    }
  }

  _spawnBots() {
    for (const nm of BOT_NAMES.slice(0, BOT_COUNT)) {
      this.bots.add(this.addPlayer(nm, true, BOT_SPEED_MULT));
    }
    for (const nm of HUNTER_NAMES) {
      this.hunterBots.add(this.addPlayer(nm, true, HUNTER_SPEED_MULT));
    }
    for (const pid of this.hunterBots) this.bots.add(pid);
  }

  _botTarget(s) {
    const h = s.head;
    for (const ob of this.obstacles) {
      if (ob.kind !== "red") continue;
      if (Math.abs(h.x - ob.x) < ob.size && Math.abs(h.y - ob.y) < ob.size) {
        return [h.x - (ob.x - h.x) * 2, h.y - (ob.y - h.y) * 2];
      }
    }
    if (h.x < 500 || h.x > MAP_W - 500 || h.y < 500 || h.y > MAP_H - 500) {
      return [MAP_W / 2 + rand(-600, 600), MAP_H / 2 + rand(-600, 600)];
    }
    const sample = [];
    const n = Math.min(90, this.foods.length);
    const idxs = new Set();
    while (idxs.size < n) idxs.add(Math.floor(Math.random() * this.foods.length));
    for (const fi of idxs) sample.push(this.foods[fi]);
    let best = sample[0];
    let bestD = Infinity;
    for (const f of sample) {
      const d = (f.x - h.x) ** 2 + (f.y - h.y) ** 2;
      if (d < bestD) { bestD = d; best = f; }
    }
    return [best.x + rand(-30, 30), best.y + rand(-30, 30)];
  }

  _updateBotSpeed() {
    const [, maxVal] = this._highestPlayer();
    const scale = maxVal >= 1e9 ? 4 : (maxVal >= 1e6 ? 2 : 1);
    for (const pid of this.bots) {
      const s = this.players.get(pid);
      if (!s) continue;
      const base = this.policeBots.has(pid) ? POLICE_SPEED_MULT
        : (this.hunterBots.has(pid) ? HUNTER_SPEED_MULT : BOT_SPEED_MULT);
      s.speedMult = base * scale;
    }
  }

  _updateBots() {
    for (const pid of this.bots) {
      if (this.policeBots.has(pid) || this.hunterBots.has(pid)) continue;
      const s = this.players.get(pid);
      if (!s || !s.alive || !s.cubes.length) continue;
      const [tx, ty] = this._botTarget(s);
      const boost = s.energy > 55 && Math.random() < 0.35;
      this.inputs[pid] = [tx, ty, boost];
    }
  }

  _hunterTarget(s) {
    const h = s.head;
    if (h.x < 400 || h.x > MAP_W - 400 || h.y < 400 || h.y > MAP_H - 400) {
      return [[MAP_W / 2 + rand(-600, 600), MAP_H / 2 + rand(-600, 600)], false];
    }
    let bestPid = null, bestD2 = Infinity;
    for (const [tp, ts] of this.players) {
      if (tp === s.pid || ts.isBot || !ts.alive || !ts.cubes.length) continue;
      const th = ts.head;
      const d2 = (th.x - h.x) ** 2 + (th.y - h.y) ** 2;
      if (d2 < bestD2) { bestD2 = d2; bestPid = tp; }
    }
    if (bestPid === null) return [this._botTarget(s), false];
    const tgt = this.players.get(bestPid);
    const th = tgt.head;
    let px, py;
    if (tgt.cubes.length > 1) {
      const vx = tgt.cubes[0].x - tgt.cubes[1].x;
      const vy = tgt.cubes[0].y - tgt.cubes[1].y;
      const lead = Math.min(40, Math.sqrt(bestD2) * 0.15);
      px = th.x + vx * lead;
      py = th.y + vy * lead;
    } else {
      px = th.x; py = th.y;
    }
    return [[px, py], bestD2 < 450 * 450];
  }

  _updateHunters() {
    for (const pid of this.hunterBots) {
      const s = this.players.get(pid);
      if (!s || !s.alive || !s.cubes.length) continue;
      const [[tx, ty], close] = this._hunterTarget(s);
      const boost = (close && s.energy > 25) || (s.energy > 60 && Math.random() < 0.4);
      this.inputs[pid] = [tx, ty, boost];
    }
  }

  _highestPlayer() {
    let bestPid = null, bestVal = 0;
    for (const [pid, s] of this.players) {
      if (s.alive && s.cubes.length && !s.isBot) {
        const v = s.cubes[0].value;
        if (v > bestVal) { bestVal = v; bestPid = pid; }
      }
    }
    return [bestPid, bestVal];
  }

  _updatePolice(dt) {
    const [tgtPid, tgtVal] = this._highestPlayer();
    if (tgtPid === null || tgtVal < BUFF_THRESHOLD) {
      this.policeTimer = 0;
      return;
    }
    this.policeTimer += dt;
    if (this.policeTimer >= POLICE_INTERVAL && this.policeBots.size < POLICE_MAX) {
      this.policeTimer = 0;
      this._spawnPolice(tgtPid, tgtVal);
    }
    for (const pid of this.policeBots) {
      const bot = this.players.get(pid);
      if (!bot || !bot.alive || !bot.cubes.length) continue;
      let tgt = this.players.get(tgtPid);
      if (tgt && tgt.alive && tgt.cubes.length) {
        const h = tgt.cubes[0];
        this.inputs[pid] = [h.x, h.y, true];
      } else {
        const [npid] = this._highestPlayer();
        if (npid !== null) {
          const h = this.players.get(npid).cubes[0];
          this.inputs[pid] = [h.x, h.y, true];
        }
      }
    }
  }

  _spawnPolice(targetPid, targetVal) {
    const tgt = this.players.get(targetPid);
    if (!tgt || !tgt.cubes.length) return;
    const h = tgt.cubes[0];
    const ang = rand(0, Math.PI * 2);
    const dist = rand(1200, 1800);
    const px = clamp(h.x + Math.cos(ang) * dist, 200, MAP_W - 200);
    const py = clamp(h.y + Math.sin(ang) * dist, 200, MAP_H - 200);
    const idx = this.policeBots.size + 1;
    const name = ("CANHSAT" + idx).slice(0, MAX_NAME);
    const pid = this.nextPid++;
    this.players.set(pid, new Snake(pid, px, py, Math.max(2, targetVal * 2), name, true, POLICE_SPEED_MULT));
    this.inputs[pid] = [h.x, h.y, true];
    this.bots.add(pid);
    this.policeBots.add(pid);
  }

  // ---------- buoc tinh toan ---------- //
  step(dt) {
    this.time += dt;
    while (this.foods.length < FOOD_COUNT) this.foods.push(this._randFood());
    while (this.powerups.length < POWERUP_COUNT) this.powerups.push(this._randPowerup());
    this.powerups = this.powerups.filter(p => this.time - p.born < POWERUP_LIFE);
    this.foods = this.foods.filter(f => !f.expire || this.time < f.expire);

    this._updateBotSpeed();
    this._updateBots();
    this._updateHunters();
    this._updateMystery(dt);
    this._updatePolice(dt);

    for (const [pid, snake] of this.players) {
      if (!snake.alive) {
        snake.respawn -= dt;
        if (snake.respawn <= 0) {
          snake.respawnAt(rand(300, MAP_W - 300), rand(300, MAP_H - 300));
          if (this.policeBots.has(pid)) {
            let mx = 2;
            for (const s of this.players.values()) {
              if (s.alive && s.cubes.length && !s.isBot) mx = Math.max(mx, s.cubes[0].value);
            }
            snake.cubes[0].value = Math.max(2, mx * 2);
          }
        }
        continue;
      }
      const inp = this.inputs[pid];
      if (inp) {
        snake.setTarget(inp[0], inp[1]);
        snake.update(dt, inp[2]);
      } else {
        snake.update(dt, false);
      }
      this._resolveGreens(snake);
    }

    this._handleFood();
    this._handlePowerups();
    for (const snake of this.players.values()) {
      this._merge(snake);
      this._enforceCubeCap(snake);
    }
    this._handleRedObstacles();
    this._handleCollisions();

    if (this.foods.length > FOOD_CAP) this.foods.length = FOOD_CAP;
  }

  _updateMystery(dt) {
    if (this.mysteryBox === null) {
      this.mysteryTimer += dt;
      if (this.mysteryTimer >= MYSTERY_INTERVAL) {
        this.mysteryTimer = 0;
        this.mysteryBox = { x: rand(500, MAP_W - 500), y: rand(500, MAP_H - 500), born: this.time };
      }
      return;
    }
    if (this.time - this.mysteryBox.born > MYSTERY_LIFE) {
      this.mysteryBox = null;
      return;
    }
    for (const snake of this.players.values()) {
      if (!snake.alive || !snake.cubes.length) continue;
      const h = snake.cubes[0];
      if (Math.abs(h.x - this.mysteryBox.x) < CUBE * 0.9 && Math.abs(h.y - this.mysteryBox.y) < CUBE * 0.9) {
        const good = Math.random() < 0.6;
        for (const c of snake.cubes) {
          c.value = good ? Math.max(2, c.value * 16) : Math.max(2, Math.floor(c.value / 16));
        }
        snake.energy = ENERGY_MAX;
        snake.energyLock = MYSTERY_ENERGY_TIME;
        this.mysteryBox = null;
        break;
      }
    }
  }

  _randFood() {
    const val = weightedChoice([2, 4, 8, 16], [90, 5, 3, 2]);
    return { x: rand(50, MAP_W - 50), y: rand(50, MAP_H - 50), value: val };
  }

  _randPowerup() {
    const kind = weightedChoice(PU_KINDS, PU_WEIGHTS);
    return { x: rand(200, MAP_W - 200), y: rand(200, MAP_H - 200), kind, born: this.time };
  }

  // ---------- vat can xanh ---------- //
  _resolveGreens(snake) {
    if (!snake.alive || !snake.cubes.length) return;
    const h = snake.head;
    for (let iter = 0; iter < 2; iter++) {
      for (const ob of this.obstacles) {
        if (ob.kind !== "green") continue;
        const half = ob.size / 2 + CUBE * 0.4;
        const dx = h.x - ob.x;
        const dy = h.y - ob.y;
        const ox = half - Math.abs(dx);
        const oy = half - Math.abs(dy);
        if (ox > 0 && oy > 0) {
          if (ox < oy) h.x = ob.x + (dx >= 0 ? half : -half);
          else h.y = ob.y + (dy >= 0 ? half : -half);
        }
      }
    }
    h.x = clamp(h.x, CUBE, MAP_W - CUBE);
    h.y = clamp(h.y, CUBE, MAP_H - CUBE);
  }

  // ---------- an khoi ---------- //
  _handleFood() {
    const grid = new Map();
    for (let fi = 0; fi < this.foods.length; fi++) {
      const f = this.foods[fi];
      const key = (Math.floor(f.x / GRID_CELL)) + "," + (Math.floor(f.y / GRID_CELL));
      if (!grid.has(key)) grid.set(key, []);
      grid.get(key).push(fi);
    }
    const eaten = new Set();
    for (const snake of this.players.values()) {
      if (!snake.alive) continue;
      for (const cube of snake.cubes) {
        const cx = Math.floor(cube.x / GRID_CELL);
        const cy = Math.floor(cube.y / GRID_CELL);
        for (let dgx = -1; dgx <= 1; dgx++) {
          for (let dgy = -1; dgy <= 1; dgy++) {
            const cell = grid.get((cx + dgx) + "," + (cy + dgy));
            if (!cell) continue;
            for (const fi of cell) {
              if (eaten.has(fi)) continue;
              const f = this.foods[fi];
              if (Math.abs(cube.x - f.x) < CUBE * 0.8 && Math.abs(cube.y - f.y) < CUBE * 0.8) {
                snake.cubes.push({ x: cube.x, y: cube.y, value: f.value });
                eaten.add(fi);
              }
            }
          }
        }
      }
    }
    if (eaten.size) {
      this.foods = this.foods.filter((_, i) => !eaten.has(i));
    }
  }

  _handlePowerups() {
    for (const snake of this.players.values()) {
      if (!snake.alive || !snake.cubes.length) continue;
      const h = snake.cubes[0];
      for (let pi = this.powerups.length - 1; pi >= 0; pi--) {
        const p = this.powerups[pi];
        if (Math.abs(h.x - p.x) < CUBE * 0.8 && Math.abs(h.y - p.y) < CUBE * 0.8) {
          this._applyPowerup(snake, p.kind);
          this.powerups.splice(pi, 1);
          break;
        }
      }
    }
  }

  _applyPowerup(snake, kind) {
    if (!snake.cubes.length) return;
    for (const c of snake.cubes) {
      let v = c.value;
      if (kind === "x2") v *= 2;
      else if (kind === "x4") v *= 4;
      else if (kind === "/2") v = Math.max(2, Math.floor(v / 2));
      else if (kind === "/4") v = Math.max(2, Math.floor(v / 4));
      c.value = v;
    }
  }

  _merge(snake) {
    if (!snake.alive || !snake.cubes.length) return;
    let vals = snake.cubes.map(c => c.value).sort((a, b) => b - a);
    while (true) {
      const out = [];
      for (const v of vals) {
        if (out.length && out[out.length - 1] === v) out[out.length - 1] *= 2;
        else out.push(v);
      }
      if (out.length === vals.length) break;
      vals = out.sort((a, b) => b - a);
    }
    for (let i = 0; i < vals.length; i++) snake.cubes[i].value = vals[i];
    snake.cubes.length = vals.length;
  }

  _enforceCubeCap(snake) {
    if (!snake.cubes.length || snake.cubes.length <= MAX_CUBES) return;
    let sum = 0;
    for (let i = MAX_CUBES; i < snake.cubes.length; i++) sum += snake.cubes[i].value;
    snake.cubes[MAX_CUBES - 1].value += sum;
    snake.cubes.length = MAX_CUBES;
  }

  _handleRedObstacles() {
    for (const snake of this.players.values()) {
      if (!snake.alive || !snake.cubes.length) continue;
      const h = snake.cubes[0];
      for (const ob of this.obstacles) {
        if (ob.kind !== "red") continue;
        if (Math.abs(h.x - ob.x) < ob.size / 2 && Math.abs(h.y - ob.y) < ob.size / 2) {
          this._kill(snake);
          break;
        }
      }
    }
  }

  _handleCollisions() {
    const grid = new Map();
    for (const [pid, s] of this.players) {
      if (!s.alive || !s.cubes.length) continue;
      for (let idx = 0; idx < s.cubes.length; idx++) {
        const c = s.cubes[idx];
        const key = Math.floor(c.x / GRID_CELL) + "," + Math.floor(c.y / GRID_CELL);
        if (!grid.has(key)) grid.set(key, []);
        grid.get(key).push([pid, idx]);
      }
    }

    for (const [apid, attacker] of [...this.players]) {
      if (!attacker.alive || !attacker.cubes.length) continue;
      const h = attacker.cubes[0];
      const hv = h.value;
      const cgx = Math.floor(h.x / GRID_CELL);
      const cgy = Math.floor(h.y / GRID_CELL);
      let done = false;
      for (let dgx = -1; dgx <= 1 && !done; dgx++) {
        for (let dgy = -1; dgy <= 1 && !done; dgy++) {
          const cell = grid.get((cgx + dgx) + "," + (cgy + dgy));
          if (!cell) continue;
          for (const [bpid, bidx] of cell) {
            if (bpid === apid) continue;
            const defender = this.players.get(bpid);
            if (!defender || !defender.alive || bidx >= defender.cubes.length) continue;
            const bc = defender.cubes[bidx];
            if (Math.abs(h.x - bc.x) >= CUBE * 0.7 || Math.abs(h.y - bc.y) >= CUBE * 0.7) continue;
            if (bidx === 0) {
              if (hv > bc.value) this._kill(defender);
              else if (hv < bc.value) this._kill(attacker);
            } else if (hv >= bc.value) {
              const bitten = defender.cubes.slice(bidx);
              defender.cubes.length = bidx;
              if (!defender.cubes.length) this._kill(defender);
              else attacker.cubes.push({ x: h.x, y: h.y, value: bitten[0].value });
              for (let ci = 1; ci < bitten.length; ci++) {
                this.foods.push({
                  x: bitten[ci].x + rand(-25, 25),
                  y: bitten[ci].y + rand(-25, 25),
                  value: bitten[ci].value,
                  expire: this.time + DEATH_FOOD_LIFE,
                });
              }
            } else {
              this._kill(attacker);
            }
            done = true;
            break;
          }
        }
      }
    }
  }

  _kill(snake) {
    if (!snake.alive) return;
    for (const [x, y, v] of snake.die()) {
      this.foods.push({
        x: clamp(x + rand(-30, 30), 30, MAP_W - 30),
        y: clamp(y + rand(-30, 30), 30, MAP_H - 30),
        value: v,
        expire: this.time + DEATH_FOOD_LIFE,
      });
    }
  }

  // ---------- dong goi trang thai ---------- //
  serialize(viewerPid = null) {
    let vx = null, vy = null;
    if (viewerPid !== null) {
      const s = this.players.get(viewerPid);
      if (s && s.cubes.length) { vx = s.head.x; vy = s.head.y; }
    }
    const near = (x, y) => vx === null || (Math.abs(x - vx) <= VIEW_HALF_W && Math.abs(y - vy) <= VIEW_HALF_H);

    const players = [];
    for (const [pid, s] of this.players) {
      players.push({
        id: pid, name: s.name, bot: s.isBot, alive: s.alive,
        energy: Math.round(s.energy * 10) / 10, respawn: Math.round(s.respawn * 10) / 10,
        score: s.score, length: s.length,
        police: this.policeBots.has(pid),
        energy_lock: Math.round(s.energyLock * 10) / 10,
        cubes: s.cubes.map(c => [Math.round(c.x * 10) / 10, Math.round(c.y * 10) / 10, c.value]),
        can_buff: s.alive && s.cubes.length > 0 && s.cubes[0].value >= BUFF_THRESHOLD && !s.energyBuffUsed,
        buff_used: s.energyBuffUsed,
      });
    }

    const foods = [];
    for (const f of this.foods) {
      if (!near(f.x, f.y)) continue;
      const item = [Math.round(f.x * 10) / 10, Math.round(f.y * 10) / 10, f.value];
      if (f.expire) item.push(Math.round(Math.max(0, f.expire - this.time) * 10) / 10);
      foods.push(item);
    }

    const powerups = this.powerups.map(p => [
      Math.round(p.x * 10) / 10, Math.round(p.y * 10) / 10, p.kind,
      Math.round((POWERUP_LIFE - (this.time - p.born)) * 10) / 10,
    ]);

    const obstacles = this.obstacles.map(o => [
      Math.round(o.x * 10) / 10, Math.round(o.y * 10) / 10, Math.round(o.size * 10) / 10, o.kind, o.shape,
    ]);

    let mystery;
    if (this.mysteryBox !== null) {
      mystery = [
        Math.round(this.mysteryBox.x * 10) / 10, Math.round(this.mysteryBox.y * 10) / 10,
        Math.round(Math.max(0, MYSTERY_LIFE - (this.time - this.mysteryBox.born)) * 10) / 10, 0,
      ];
    } else {
      mystery = [-1, -1, 0, Math.round(Math.max(0, MYSTERY_INTERVAL - this.mysteryTimer) * 10) / 10];
    }

    return { players, foods, powerups, obstacles, mystery, map: [MAP_W, MAP_H] };
  }
}

module.exports = { GameWorld, Snake, TICK, MAP_W, MAP_H, CUBE };
