# AGENTS.md — Cubes 2048 (multiplayer)

File nay la **bản đồ dự án** cho AI (opencode). Doc ky truoc khi sua code.
Ghi chu: toan bo comment/giao dien dung **tieng Viet (khong dau)** de nhat quan voi code hien co.

---

## 1. Tong quan

Game multiplayer giong **Cubes 2048.io** + slither.io: ban la mot "con ran" gom chuoi
khoi co gia tri (2, 4, 8, ...). An khoi nho de lon len, gop khoi cung gia tri (2048-style),
cam dau vao nguoi khac de chet hoac bi chet. Cuoi cung lon nhat thang.

- **Ngon ngu:** Python 3 (server) + HTML/Canvas/JS (client web) + Pygame (client desktop).
- **Chua co git repo.** Nen khoi tao `git init` va commit ngay khi bat dau lam viec.
- **3 kieu chay:** TCP desktop (server.py), Web local (server_web.py), Cloud 1-cong (server_cloud.py).
- Tat ca server dung chung logic o **`game_core.py`** (day la trai tim cua game).

---

## 2. Cau truc file

| File | Vai tro | Phu thuoc |
|------|---------|-----------|
| `game_core.py` | **Logic game thuan** (khong mang, khong do hoa). Lop `Snake`, `GameWorld`. Tat ca server import chung. | stdlib only |
| `server.py` | Server **TCP** cho client desktop Pygame. Length-prefixed JSON. Port 5555. | stdlib |
| `server_web.py` | Server **Web local**: HTTP (index.html) + WebSocket rieng 2 cong. ws 8765 / http 8080. | `websockets` |
| `server_cloud.py` | Server **Cloud 1 cong** (aiohttp): phuc vu HTML + WS cung PORT. San sang deploy Render/Koyeb/Fly. | `aiohttp` |
| `client.py` | Client desktop **Pygame** (chi ket noi TCP server.py). Nhap Ten/IP/Port. | `pygame` |
| `index.html` | Client **Web** (Canvas + JS). Tu do served boi server_web.py hoac server_cloud.py. Tu nhan ws/wss theo host. | none |
| `requirements.txt` | Hien chi co `aiohttp`. (luu y: `pygame` + `websockets` chua duoc liet ke — bo sung neu can) | - |

### Luong du lieu (client -> server)
Tat ca client gui cung 3 loai message JSON:
- `{"type":"join","name": "..."}`  — dat ten (sau welcome)
- `{"type":"input","mx":x,"my":y,"boost":bool}` — vi tri muc tieu (world coords) + boost
- `{"type":"sac"}` — hy sinh ½ gia tri dau ran (>= 1M) de hoi day nang luong

Server phan hoi:
- `{"type":"welcome","id":pid}` — cap pid
- `{"type":"state","data":{...}}` — trang thai game (20 lan/giay, ~0.05s)
- `{"type":"full"}` — phong day (max 20 nguoi choi)

### Format trang thai (`GameWorld.serialize`)
```jsonc
{
  "players": [{ "id","name","bot","alive","energy","respawn","score","length",
                "police","energy_lock","can_buff","buff_used",
                "cubes":[[x,y,value],...] }],   // cubes[0] = dau
  "foods":    [[x,y,value(,expireRemain)]],     // item 4 = death food (co han)
  "powerups": [[x,y,kind,remain]],              // kind: "x2"|"x4"|"/2"|"/4"
  "obstacles":[[x,y,size,kind,shape]],          // kind: "green"|"red"; shape: square/circle/...
  "mystery":  [[x,y,remain,0]],                 // x>=0: dang xuat hien; x<0: dang cooldown (doc cd[3])
  "map":      [MAP_W, MAP_H]
}
```
LUU Y: `mystery` luon la list 1 phan tu. Client phan biet active (x>=0) vs cooldown (x<0, doc gia tri `[3]`).

---

## 3. Chay & test nhanh

```powershell
# === Web local (de nhat, mo tren 2 tab de test multiplayer) ===
cd E:\Cubes2048
pip install websockets
python server_web.py                 # ws=8765 http=8080
# mo trinh duyet: http://localhost:8080

# === Cloud 1 cong (deploy hoac test local) ===
pip install aiohttp
python server_cloud.py               # PORT mac dinh 8080

# === Desktop TCP (can 2 cua so) ===
python server.py                     # port 5555
python client.py                     # nhap IP 127.0.0.1 port 5555
```

**Kiem tra compile (khong can chay server):**
```powershell
python -m py_compile game_core.py server.py server_web.py server_cloud.py client.py
```

> Luu y client web `index.html` mac dinh ket noi `ws://localhost:8080`. Khi server_web chay,
> WS o cong **8765** nen phai sua URL input thanh `ws://localhost:8765`, hoac dung `server_cloud.py`
> (HTML+WS cung cong 8080) de khong phai doi URL.

---

## 4. Game mechanics (chi tiet — doc ky truoc sua game_core.py)

### 4.1 Con ran (`Snake`)
- `cubes[0]` = **dau** (head), luon o vi tri dau. Con lai la than.
- Di chuyen: dau chay huong `target` (gui tu client). Than **bám theo vet dau** (deque `path`),
  moi khoi cach `SPACING` pix tren duong path -> hieu ung nhu rang con ran uon luon.
- **Tang toc (boost):** tieu `ENERGY_DRAIN`/giay. Het nang luong -> ve `ENERGY_REGEN`. Speed = BOOST_SPEED.
- **Chet:** `respawn` 3 giay roi hoi sinh ngau nhien bang 1 khoi value 2.
- Score = tong value cac khoi. Length = so khoi (cap tai `MAX_CUBES=40`).

### 4.2 An khoi (`_handle_food`)
- Bat ky **cube nao** cua ran (khong chi dau) cham food (overlap < CUBE*0.8) -> them khoi moi.
- **Quan trong:** food duoc **append vao cuoi** (tail), KHONG phai them sau dau.
  -> Ran phai an roi cho than di qua moi cube moi. Day la y thiet ke.

### 4.3 Gop khoi (`_merge`) — 2048-style
- Sau moi step, sap xep tat ca value giam dan, gop cap bang nhau thanh x2, lap lai cho den het.
- **Day la MERGE TOAN THAN, khong phai theo thu tu vi tri.** (p/p da thao luan trong session:
  y thiet ke la gop het cac cap trung -> giam do dai, tang value).
- `_enforce_cube_cap`: neu > MAX_CUBES, don het phan du vao cube cuoi.

### 4.4 Va cham nguoi choi (`_handle_collisions`)
- Dau A (value hv) cham cube B:
  - **Vo dau (bidx==0):** hv > bc -> B chet; hv < bc -> A chet; bang -> khong sao.
  - **Vo than (bidx>0):** hv >= bc -> can phan con lai cua B (them 1 cube vao A, phan bi can
    thanh food co han 3s); hv < bc -> A chet.
- Dung **spatial grid** (`GRID_CELL=160`) de giam vong lap. KHONG xoa grid khi chinh sua nhe.

### 4.5 Vat can "KE XAU" (obstacles)
- **Xanh (green):** chan dau (day ra), khong chet (`_resolve_greens`). 6 cai.
- **Do (red):** cham dau = **chet lien** (`_handle_red_obstacles`). 4 cai.
- Co nhieu hinh dang (square/circle/triangle/hexagon/.../spiral) — chi la hinh uc.

### 4.6 Power-ups (`_handle_powerups`)
- Chi **dau** cham. Ap dung len **toan bo cube**: x2 / x4 / /2 / /4 (min 2).
- Ton tai `POWERUP_LIFE=5s` roi bien mat.

### 4.7 Cac co che dac biet (late-game)
- **Mystery box** (`_update_mystery`): moi 300s xuat hien 30s. An -> 60% x16 toan than,
  40% //16. + khoa nang luong vo han 30s.
- **Police (Canh sat):** khi nguoi choi real lon nhat >= `BUFF_THRESHOLD(1M)`, moi 180s sinh
  toi 5 bot CANHSAT co value gap doi, doi toc san duoi nguoi do.
- **Buff hy sinh:** dau >= 1M, nhan [E] -> /2 dau, hoi day nang luong (1 lan/mang).
- **Bot AI:** 3 bot thuong (an food) + 3 hunter (duoi nguoi choi). Speed scale theo nguoi choi lon nhat.

---

## 5. Client web (`index.html`) — luu y hieu suat

- **Sprite caching:** moi gia tri cube/food/obstacle/powerup/aura duoc render 1 lan len canvas
  offscreen roi reuse (`getSprite`, `getFoodSprite`, `getObSprite`...). Don sprite moi 5s neu > 100.
- **Interpolation** giua 2 state (`interpPlayers`) de chay muot 60fps khi server chi gui 20fps.
- **Dragon styles:** 5 ten dac biet (DAOCV/KID/MAPDIA/SUMO/CANON) co hieu ung than/long/mat rieng.
  DAOCV >= 1M bien thanh 3 dau (triple head).
- Phat hien su kien (an/gop/chet) bang so sanh frame (`detectEvents`) -> sinh particle.
- Phan biet **mobile** (`LO = pointer:coarse`): tat shadow/vignette de giam tai.

---

## 6. Convention code

- **Comment/giao dien: tieng Viet khong dau** (vd "Dang cho du lieu tu server"). Giu nguyen style nay.
- Ten bien ham: **tieng Anh** (`_handle_food`, `cube_color`, `serialize`).
- Toan bo game logic khong phu thuoc thu vien -> de test. Chi server_web can `websockets`,
  server_cloud can `aiohttp`, client can `pygame`.
- Constant ALL_CAPS o dau `game_core.py` (MAP_W, CUBE, TICK...).
- Private method bat dau `_`.
- **Chua co tests tu dong.** Khi sua game_core, nen test nhanh bang `python -c "..."` import
  GameWorld va goi `step()` / `serialize()`.

---

## 7. Van de da biet / can de y

1. **`requirements.txt` chua du:** hien chi co `aiohttp`. Them `pygame` va `websockets` khi can.
2. **URL WS khac cong giua 2 server web:** server_web = HTTP 8080 + WS 8765 (2 cong),
   server_cloud = ca 2 o cung PORT. Client mac dinh noi `ws://localhost:8080` -> phu hop
   server_cloud. Neu chay server_web phai doi URL input thanh `ws://localhost:8765`.
3. **MAP_W/MAP_H khac nhau:** game_core = 9000x9000, client.py = 6000x6000 (chi la default,
   client lay tu `state.map`). index.html lay tu server. De y khi can dong bo.
4. **Chua co git.** Luu y: `/undo`, `/redo` cua opencode can git -> hien khong dung duoc.
   De xet: `git init` + commit ban dau.
5. **Session opencode cu** (neu can tim lai): session "Game Cubes 2048.io multiplayer" co
   cwd = `C:/Windows/System32` (do lan truoc mo tu terminal Admin). Chay opencode tu do hoac
   dung `opencode -s <sessionID>` de resume.

---

## 8. Ky vong khi AI lam viec

- **Luon doc `game_core.py` truoc** khi thay game logic — no la nguon su that duy nhat.
- Sua xong chay `python -m py_compile` tat ca file .py de bao dam khong loi cu phap.
- Giu comment tieng Viet khong dau, ten tieng Anh.
- Neu them tinh nang mang/protocol -> cap nhat ca 3 server (server.py, server_web.py, server_cloud.py)
  vi chung phai dong bo message format.
- Neu doi constant game -> cap nhat ca game_core.py va (neu can) client.py / index.html.
