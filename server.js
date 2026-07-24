"use strict";
const http = require("http");
const fs = require("fs");
const path = require("path");
const { WebSocketServer } = require("ws");
const { GameWorld, TICK } = require("./game_core");

const PORT = parseInt(process.env.PORT || "8080", 10);
const MAX_PLAYERS = 50;
const PLAYER_TIMEOUT = 30; // giay khong hoat dong -> xoa
const WEB_DIR = __dirname;

const world = new GameWorld();
const conns = new Map();   // pid -> { ws, lastSeen }

// --------------------- phuc vu HTML --------------------- //
const server = http.createServer((req, res) => {
  if (req.url === "/" || req.url === "/index.html") {
    const html = fs.readFileSync(path.join(WEB_DIR, "index.html"), "utf8");
    res.writeHead(200, {
      "Content-Type": "text/html; charset=utf-8",
      "Cache-Control": "no-cache, no-store, must-revalidate",
    });
    res.end(html);
  } else {
    res.writeHead(404);
    res.end("Not found");
  }
});

const wss = new WebSocketServer({ server });

// --------------------- ping + timeout --------------------- //
setInterval(() => {
  const now = Date.now() / 1000;
  for (const [pid, info] of conns) {
    const ws = info.ws;
    if (ws.readyState === ws.OPEN) {
      if (now - info.lastSeen > PLAYER_TIMEOUT) {
        console.log(`[NODE] Player ${pid} timeout (ghost) -> xoa`);
        ws.terminate();
      } else {
        ws.ping();
      }
    }
  }
}, 10000);

function cleanupPid(pid) {
  conns.delete(pid);
  world.removePlayer(pid);
}

// --------------------- xu ly 1 client --------------------- //
wss.on("connection", (ws) => {
  if (conns.size >= MAX_PLAYERS) {
    ws.send(JSON.stringify({ type: "full" }));
    ws.close();
    return;
  }
  const pid = world.addPlayer();
  const now = Date.now() / 1000;
  conns.set(pid, { ws, lastSeen: now });
  ws.send(JSON.stringify({ type: "welcome", id: pid }));
  console.log(`[NODE] Player ${pid} vao phong`);

  ws.on("message", (data) => {
    const info = conns.get(pid);
    if (info) info.lastSeen = Date.now() / 1000;
    let msg;
    try { msg = JSON.parse(data); } catch { return; }
    const t = msg.type;
    if (t === "input") {
      world.setInput(pid, msg.mx || 0, msg.my || 0, !!msg.boost);
    } else if (t === "join") {
      world.setName(pid, msg.name || "");
    } else if (t === "sac") {
      world.sacrifice(pid);
    }
  });

  ws.on("pong", () => {
    const info = conns.get(pid);
    if (info) info.lastSeen = Date.now() / 1000;
  });

  ws.on("error", () => {});

  ws.on("close", () => {
    cleanupPid(pid);
    console.log(`[NODE] Player ${pid} thoat`);
  });
});

// --------------------- vong lap game --------------------- //
let last = Date.now();
let sendAcc = 0;

function gameLoop() {
  const now = Date.now();
  const dt = Math.min((now - last) / 1000, 0.1);
  last = now;

  world.step(dt);
  sendAcc += dt;

  if (sendAcc >= 0.05) {
    sendAcc = 0;
    const dead = [];
    for (const [pid, info] of conns) {
      const ws = info.ws;
      if (ws.readyState !== ws.OPEN) { dead.push(pid); continue; }
      const payload = JSON.stringify({ type: "state", data: world.serialize(pid) });
      ws.send(payload, (err) => { if (err) dead.push(pid); });
    }
    for (const pid of dead) cleanupPid(pid);
  }
}

setInterval(gameLoop, TICK * 1000);

server.listen(PORT, "0.0.0.0", () => {
  console.log(`[NODE] Server tai http://0.0.0.0:${PORT}  (HTML + WS cung cong)`);
});
