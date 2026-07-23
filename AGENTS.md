# Cubes 2048 - Thu thach cung Minh Dat

Multiplayer snake + 2048 merge game. Node.js server, browser client.

## Quick Start

```bash
npm install
npm start          # http://localhost:8080
```

## Architecture

| File | Role |
|---|---|
| **`game_core.js`** | All game logic: Snake class, GameWorld class, bots, police, collisions, food, powerups, mystery box, serialization. No networking. |
| **`server.js`** | Single-port HTTP + WebSocket server. Serves `index.html` + runs game loop at 60fps, sends state at 20fps. Deploy target for Render/VPS. |
| **`index.html`** | Browser client: Canvas rendering, sprite caching, interpolation, input handling, HUD, minimap. Connects via WebSocket. |
| **`package.json`** | Dependencies (`ws`), `npm start` = `node server.js`. |
| **`render.yaml`** | Render.com config: runtime=node, build=`npm install`, start=`node server.js`. |

### Legacy (Python - not used for deployment)

| File | Role |
|---|---|
| `game_core.py` | Python version of game logic (frozen). |
| `server_cloud.py` / `server_web.py` / `server.py` | Python servers (frozen). |
| `client.py` | Pygame desktop client (frozen). |
| `python-backup/` | Full backup of Python version before migration. |

## Game Design

### Core Loop
- Player controls a snake on a 9000x9000 map.
- Eat food cubes (value 2/4/8/16) to grow.
- Same-value cubes auto-merge (2048 style): 2+2=4, 4+4=8, etc.
- Bite enemy snake body (your head value >= their cube value) to cut them.
- Head-on collision: higher value wins. Equal = pass through.
- Death = all cubes scatter as food (3s expiry). Respawn after 3s.

### Key Constants (top of `game_core.js`)

```
MAP_W, MAP_H = 9000, 9000       # Map size
CUBE = 40, SPACING = 40         # Cube size, distance between body cubes
NORMAL_SPEED = 170              # Base speed (px/s)
BOOST_SPEED = 300               # Boost speed (px/s)
MAX_CUBES = 25                  # Max body length per snake
FOOD_COUNT = 1500               # Food maintained on map
FOOD_CAP = 1500                 # Hard food limit
MAX_PLAYERS = 50                # Connection limit (in server.js)
```

### Bots (AI snakes)

| Type | Names | Behavior | Speed |
|---|---|---|---|
| **Passive** | HocNgu, LuoiBieng, HonLao | Eat nearest food, avoid red obstacles | 2.0x base |
| **Hunter** | ChuaTe, MaDoc, SatThu | Hunt nearest human player, intercept path | 0.8x base |
| **Police** | CANHSAT1-5 | Spawn every 3min when any player >1M, value=2x highest player | 0.4x (fixed, no scaling) |

Bot speed scaling: when any player >1M, passive/hunter bots get 2x; >1B get 4x.
**Police bots are exempt from scaling** — always 0.4x.

### Powerups
- Types: x2, x4, /2, /4 (weights: 40/12/30/18)
- Spawn: 8 active at all times, 5s lifetime
- Applied to all cubes on pickup

### Mystery Box
- Spawns every 5 min, lasts 30s
- 60% chance: all cubes x16. 40%: all cubes /16 (floor 2)
- Bonus: 30s infinite energy

### Energy System
- Boost drains energy (45/s), regen 25/s, max 100
- Press E (sacrifice): if head >1M, halve head value → full energy (1x/life)
- Mystery box grants 30s energy lock (infinite boost)

### Obstacles ("KE XAU")
- Green (6): block movement, push head out (no death)
- Red (4): instant death on touch
- 9 random shapes per obstacle

### Dragon System (client-side only)
- Value >= 1M = "Dragon" with special head rendering + aura
- 5 dragon head styles by name: DAOCV, KID, MAPDIA, SUMO, CANON
- DAOCV >1M gets triple heads
- Aura rendered as cached sprite with pulse effect

## Network Protocol

WebSocket JSON messages (client ↔ server):

```
Server → Client:
  {type: "welcome", id: <pid>}
  {type: "state", data: <serialized world>}
  {type: "full"}

Client → Server:
  {type: "join", name: <string>}
  {type: "input", mx: <float>, my: <float>, boost: <bool>}
  {type: "sac"}
```

### State Serialization (`serialize(viewerPid)`)
- Per-viewer viewport culling: only sends entities within VIEW_HALF_W × VIEW_HALF_H of viewer
- Players: id, name, bot, alive, energy, score, cubes[[x,y,value]], police, energy_lock, can_buff
- Foods: [x, y, value] or [x, y, value, expire] (death food)
- Powerups: [x, y, kind, remaining_life]
- Obstacles: [x, y, size, kind, shape]
- Mystery: [x, y, remaining, 0] (active) or [-1, -1, 0, countdown] (inactive)

## Performance Optimizations

1. **Spatial grid** for food collision + player collision (GRID_CELL=160)
2. **Cube cap** (MAX_CUBES=25) with auto-merge of excess
3. **Viewport culling** in serialize — per-viewer, reduces payload size
4. **20fps send rate** with 60fps game loop — client interpolates between updates
5. **Sprite caching** on client — food, obstacle, powerup, dragon heads, aura all pre-rendered
6. **Background/grid/vignette** cached to offscreen canvases
7. **0 per-frame shadowBlur** on game objects (only HUD uses minimal blur)
8. **WebSocket ping** every 25s to prevent Render proxy timeout

## Client Features

- Canvas 2D rendering at 60fps
- Position interpolation between server updates (20fps → smooth 60fps)
- Touch controls + mobile detection (reduced effects on coarse pointers)
- Minimap (player dots only)
- Fullscreen toggle
- Color tiers: HSL-based for values >2048 (K=green, M=blue, B=purple, T=pink, Qa=gold)
- Number formatting: K/M/B/T/Qa abbreviations
- Name tag above head (no score shown)
- Arrow indicator on head cube pointing in movement direction
- Particle effects (reduced: n/3, cap 60)
- Random name generator + quick-pick buttons (DAOCV/KID/MAPDIA/SUMO/CANON)
- Duplicate name prevention (case-insensitive, append number)

## Deployment

### Render.com
1. Create Web Service from GitHub repo
2. Runtime: **Node**
3. Build: `npm install`
4. Start: `node server.js`
5. `render.yaml` included for Blueprint deploys

### VPS
```bash
npm install
PORT=80 node server.js
# Use Nginx reverse proxy for HTTPS + multiple apps on one server
```

## Development

```bash
# Run locally
npm start

# Test game logic
node -e "const {GameWorld}=require('./game_core'); const w=new GameWorld(); w.step(0.016); console.log('OK')"

# Benchmark
node -e "const {GameWorld}=require('./game_core'); /* see previous benchmarks */"
```

## Commands

- **Lint/typecheck**: None configured. Verify with `node -e` test snippets.
- **Start**: `npm start` or `node server.js`
- **Test**: No test framework. Manual testing via browser.
