#!/usr/bin/env bash
set -euo pipefail

# ======================================================
#  Cubes2048 - Oracle Cloud VPS Deploy Script
#  Usage: bash deploy.sh
#  Chay voi quyen sudo (root hoac user co sudo)
# ======================================================

RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; NC='\033[0m'
log()  { echo -e "${CYAN}[INFO]${NC} $1"; }
ok()   { echo -e "${GREEN}[OK]${NC} $1"; }
fail() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# --- Kiem tra quyen ---
if [ "$EUID" != "0" ]; then
  fail "Vui long chay bang sudo: sudo bash deploy.sh"
fi

# --- Lay user thuong (khong phai root) ---
TARGET_USER="${SUDO_USER:-ubuntu}"
TARGET_HOME="/home/$TARGET_USER"
APP_DIR="$TARGET_HOME/cubes2048"
GIT_REPO="https://github.com/daocv/cubes2048.git"

log "Bat dau deploy Cubes2048 cho user $TARGET_USER..."

# 1. Cai Node.js 20
if ! command -v node &>/dev/null; then
  log "Dang cai Node.js 20..."
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  apt-get install -y nodejs
  ok "Node.js $(node -v) da cai xong"
else
  ok "Node.js $(node -v) da co san"
fi

# 2. Cai PM2
if ! command -v pm2 &>/dev/null; then
  log "Dang cai PM2..."
  npm install -g pm2
  ok "PM2 da cai xong"
else
  ok "PM2 da co san"
fi

# 3. Tao thu muc project
if [ ! -d "$APP_DIR" ]; then
  mkdir -p "$APP_DIR"
  chown "$TARGET_USER:$TARGET_USER" "$APP_DIR"
fi

# 4. Clone / copy code
#    Neu dung git:
#    git clone "$GIT_REPO" "$APP_DIR"
#    Neu copy tu may local: dung SCP hoac FTP de day file len /home/ubuntu/cubes2048/
log "Copy code vao $APP_DIR (dung SCP hoac git clone)"
log "Neu dung SCP: scp -r ./* ubuntu@YOUR_IP:/home/ubuntu/cubes2048/"

# 5. Tao thu muc logs
mkdir -p "$APP_DIR/logs"
chown -R "$TARGET_USER:$TARGET_USER" "$APP_DIR"

# 6. Cai npm dependencies
log "Dang cai npm dependencies..."
cd "$APP_DIR"
sudo -u "$TARGET_USER" npm install --production
ok "npm dependencies da cai xong"

# 7. Mo port 8080 tren Oracle Cloud firewall
log "Cau hinh firewall (iptables) cho port 8080..."
iptables -C INPUT -p tcp --dport 8080 -j ACCEPT 2>/dev/null || iptables -A INPUT -p tcp --dport 8080 -j ACCEPT
ok "Port 8080 da duoc mo"

# 8. Luu iptables de khong mat sau reboot
if ! command -v iptables-persistent &>/dev/null; then
  apt-get install -y iptables-persistent 2>/dev/null || true
fi
netfilter-persistent save 2>/dev/null || true

# 9. Khoi dong server voi PM2
log "Khoi dong Cubes2048 voi PM2..."
cd "$APP_DIR"
sudo -u "$TARGET_USER" pm2 start ecosystem.config.js --env production
sudo -u "$TARGET_USER" pm2 save
sudo -u "$TARGET_USER" pm2 startup systemd -u "$TARGET_USER" --hp "$TARGET_HOME"
ok "Cubes2048 da chay!"

# 10. Kiem tra
sleep 2
if curl -s http://localhost:8080 > /dev/null 2>&1; then
  ok "Server dang chay tot tai http://localhost:8080"
  HOST_IP=$(curl -s ifconfig.me 2>/dev/null || echo "YOUR_SERVER_IP")
  echo ""
  echo "============================================"
  echo "  Cubes2048 DA SAN SANG!"
  echo "  Truy cap: http://$HOST_IP:8080"
  echo "============================================"
  echo ""
  echo "Quan ly PM2:"
  echo "  pm2 status           - xem trang thai"
  echo "  pm2 logs cubes2048   - xem log"
  echo "  pm2 restart cubes2048 - khoi dong lai"
  echo "  pm2 stop cubes2048   - dung server"
else
  fail "Server khong chay. Kiem tra log: pm2 logs cubes2048"
fi