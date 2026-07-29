# Huong dan deploy Cubes2048 len Oracle Cloud Free Tier

## Tong quan

Oracle Cloud Free Tier cho ban:
- 4 core ARM (Ampere A1)
- 24 GB RAM
- 200 GB o cung
- **10 TB bandwidth/thang** — thoai mai cho game, ko lo het luong
- Mien phi vinh vien (can visa xac minh, ko tru tien)

---

## Buoc 1: Dang ky Oracle Cloud

1. Vao https://www.cloud.oracle.com
2. Bam **"Start for free"**
3. Dien thong tin:
   - Email, mat khau
   - So dien thoai (nhan ma xac thuc)
   - **The Visa/Mastercard** (xac minh, KHONG bi tru tien)
4. Dang nhap vao https://cloud.oracle.com

---

## Buoc 2: Tao VM

1. Menu ☰ → **Compute** → **Instances**
2. Bam **"Create instance"**
3. Dat ten: `cubes2048`
4. **Image**: Chon **Canonical Ubuntu 22.04** (hoac 24.04)
5. **Shape**: Bam "Change shape" → chon **"Ampere"** → **VM.Standard.A1.Flex**
   - Keo OCPU len **4**
   - RAM tu dong len 24 GB
6. **Add SSH keys**: Chon **"Generate a key pair"** → tai file `.pem` ve may
   - **Giu file nay can than!** Chiay khoa de SSH vao VPS.
7. **Boot volume**: De mac dinh (200 GB)
8. Bam **"Create"** — doi ~2 phut cho VM chay.
9. Copy **Public IP Address** (can cho buoc sau).

---

## Buoc 3: Mo cong 8080 tren tuong lua Oracle

1. Menu ☰ → **Networking** → **Virtual Cloud Networks**
2. Bam vao VPC dang dung
3. Ben trai bam **"Security Lists"** → bam vao security list dang dung
4. Bam **"Add Ingress Rules"**:
   - Source CIDR: `0.0.0.0/0`
   - IP Protocol: **TCP**
   - Destination Port Range: **8080**
   - Description: `Cubes2048 game`
5. Bam **Add Ingress Rules**

---

## Buoc 4: SSH vao VPS va deploy

Mo terminal (PowerShell / CMD / Git Bash), chay:

```bash
ssh -i path/to/your-key.pem ubuntu@IP_CUA_BAN
```

Sau khi vao duoc VPS, chay 2 cau:

```bash
# Tai code tu GitHub
git clone https://github.com/daocv/cubes2048.git /home/ubuntu/cubes2048

# Deploy (tu dong cai Node, PM2, chay server)
sudo bash /home/ubuntu/cubes2048/deploy.sh
```

**That's it.** Sau ~30 giay, server se chay tai `http://IP_CUA_BAN:8080`.

---

## Buoc 5: Choi game!

Mo trinh duyet: `http://IP_CUA_BAN:8080`

Chia se link nay cho ban be la choi duoc ngay.

---

## Quan ly server

```bash
# SSH vao VPS, chay:

pm2 status              # xem trang thai
pm2 logs cubes2048      # xem log
pm2 restart cubes2048   # khoi dong lai
pm2 stop cubes2048      # dung server
pm2 start cubes2048     # chay lai
```

---

## (Nang cao) Gan domain + HTTPS

```bash
sudo apt install nginx certbot python3-certbot-nginx
sudo cp /home/ubuntu/cubes2048/nginx-cubes2048.conf /etc/nginx/sites-available/cubes2048
sudo nano /etc/nginx/sites-available/cubes2048
# Sua "domain.cua.ban" thanh domain that
sudo ln -s /etc/nginx/sites-available/cubes2048 /etc/nginx/sites-enabled/
sudo certbot --nginx -d domain.cua.ban
sudo nginx -t && sudo systemctl reload nginx
```

Sau do truy cap: `https://domain.cua.ban`

---

## Luu y

- Server chay **Node.js** (`server.js` + `game_core.js`), HTML + WebSocket cung cong 8080
- Da toi uu cho Oracle: 20fps state update, FOOD_COUNT=500, tu dong reset khi phong trong 2 phut
- 10 TB bandwidth/thang ~ 200-300 nguoi choi cung luc hang ngay (ko phai lo)
