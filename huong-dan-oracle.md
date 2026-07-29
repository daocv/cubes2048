# Hướng dẫn deploy Cubes2048 lên Oracle Cloud Free Tier

## Tổng quan

Oracle Cloud Free Tier cho bạn:
- 4 core ARM (Ampere A1)
- 24 GB RAM
- 200 GB ổ cứng
- **10 TB bandwidth/tháng** — thoải mái cho game
- Miễn phí vĩnh viễn

---

## Bước 1: Đăng ký Oracle Cloud

1. Vào https://www.oracle.com/cloud/free/
2. Click **"Start for free"**
3. Điền thông tin:
   - Email, mật khẩu
   - Số điện thoại (nhận mã xác thực)
   - **Thẻ Visa/Mastercard** (để xác minh, sẽ không bị trừ tiền)
4. Sau khi đăng ký xong, đăng nhập vào https://cloud.oracle.com

---

## Bước 2: Tạo VM (Virtual Machine)

1. Trên dashboard, click menu ☰ → **Compute** → **Instances**
2. Click **"Create instance"**
3. Đặt tên: `cubes2048`
4. **Image**: Chọn **Canonical Ubuntu 22.04** (hoặc 24.04)
5. **Shape**: Click "Change shape" → chọn **"Ampere"** → **VM.Standard.A1.Flex**
   - Kéo số OCPU lên **4** (tối đa free)
   - RAM tự động lên 24 GB
6. **Add SSH keys**: Chọn **"Generate a key pair"** → tải file `.pem` về máy
   - **Giữ file này cẩn thận!** Đây là chìa khóa để SSH vào VPS.
7. **Boot volume**: Để mặc định (200 GB)
8. Click **"Create"** — đợi ~2 phút cho VM chạy.
9. Sau khi VM sẵn sàng, nhìn vào bảng, copy **Public IP Address**.

---

## Bước 3: Mở port 8080 trên tường lửa Oracle

1. Menu ☰ → **Networking** → **Virtual Cloud Networks**
2. Click vào VPC đang dùng (thường tên có chữ "vcn")
3. Bên trái click **"Security Lists"** → click vào security list đang dùng
4. Click **"Add Ingress Rules"** và thêm:
   - Source CIDR: `0.0.0.0/0` (cho phép tất cả)
   - IP Protocol: **TCP**
   - Destination Port Range: **8080**
   - Description: `Cubes2048 game`
5. Click **Add Ingress Rules**

---

## Bước 4: Upload code lên VPS

Có 2 cách:

### Cách A: Dùng SCP (từ máy bạn, mở terminal/cmd)

Mở terminal/cmd tại thư mục `E:\Cubes2048` và chạy:

```bash
scp -i path/to/your-key.pem -r ./* ubuntu@IP_CUA_BAN:/home/ubuntu/cubes2048/
```

(Với Windows: dùng PowerShell, chạy lệnh trên sau khi cài OpenSSH)

### Cách B: Dùng git (khuyên dùng)

```bash
# Trên máy bạn: tạo repo GitHub, push code lên
# Trên VPS:
git clone https://github.com/YOUR_USERNAME/cubes2048.git /home/ubuntu/cubes2048
```

---

## Bước 5: Chạy deploy script

SSH vào VPS:

```bash
ssh -i path/to/your-key.pem ubuntu@IP_CUA_BAN
```

Sau đó chạy:

```bash
cd /home/ubuntu/cubes2048
sudo bash deploy.sh
```

(Lưu ý: sửa dòng `GIT_REPO` trong `deploy.sh` nếu dùng git, hoặc bỏ qua nếu dùng SCP)

Script sẽ tự động:
- Cài Node.js 20
- Cài PM2
- Cài npm dependencies
- Mở port 8080 trên firewall
- Chạy server với PM2 (tự động restart nếu crash)

---

## Bước 6: Chơi game!

Mở trình duyệt: `http://IP_CUA_BAN:8080`

---

## Quản lý server

```bash
# Xem trạng thái
pm2 status

# Xem log
pm2 logs cubes2048

# Restart
pm2 restart cubes2048

# Dừng
pm2 stop cubes2048

# Xem realtime log
pm2 logs cubes2048 --lines 50
```

---

## (Nâng cao) Gắn domain + HTTPS

Nếu có domain, bạn có thể dùng Nginx + Let's Encrypt:

```bash
sudo apt install nginx certbot python3-certbot-nginx
sudo cp /home/ubuntu/cubes2048/nginx-cubes2048.conf /etc/nginx/sites-available/cubes2048
sudo nano /etc/nginx/sites-available/cubes2048
# Sửa "domain.cua.ban" thành domain thật
sudo ln -s /etc/nginx/sites-available/cubes2048 /etc/nginx/sites-enabled/
sudo certbot --nginx -d domain.cua.ban
sudo nginx -t && sudo systemctl reload nginx
```

Sau đó truy cập: `https://domain.cua.ban`

---

## Tối ưu đã làm sẵn

File `server.js` đã được chỉnh:
- ✅ Broadcast 20Hz → **10Hz** (giảm 50% bandwidth)
- ✅ **permessage-deflate** (nén WebSocket)
- ✅ **Gzip** cho file HTML (giảm ~80% dung lượng trang)