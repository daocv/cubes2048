# Hướng dẫn deploy Cubes2048 lên Koyeb

## Tổng quan Koyeb Free Tier

| Tài nguyên | Free |
|------------|------|
| RAM | 512 MB |
| CPU | 1 vCPU shared |
| Bandwidth | **100 GB/tháng** |
| Credit | **$5.5/tháng** (dùng cho always-on) |
| Sleep | Có, sau 30 phút không truy cập |

**Lưu ý:** Koyeb free tier sẽ **sleep** sau 30 phút không có traffic. Người chơi đầu tiên vào sẽ chờ ~5-10 giây để server wake up. Dùng $5.5 credit để bật "always-on" (tốn ~$5/tháng).

---

## Bước 1: Đăng ký Koyeb

1. Vào **https://www.koyeb.com**
2. Click **"Start Free"**
3. Đăng ký bằng **GitHub** (nhanh nhất, không cần thẻ)
4. Nếu bắt nhập thẻ: có thể bỏ qua bằng cách chọn free plan

---

## Bước 2: Push code lên GitHub

Trong `E:\Cubes2048`, mở terminal/cmd chạy:

```bash
git init
git add .
git commit -m "first commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/cubes2048.git
git push -u origin main
```

(Thay `YOUR_USERNAME` bằng GitHub username của bạn)

---

## Bước 3: Deploy lên Koyeb

1. Login Koyeb → dashboard
2. Click **"Create App"**
3. Chọn **"GitHub"** → kết nối GitHub → chọn repo `cubes2048`
4. Koyeb tự động nhận diện Node.js, để mặc định:
   - **Build command**: `npm install`
   - **Run command**: `node server.js`
   - **Port**: `8080`
5. Click **"Create App"**
6. Đợi ~2 phút, bạn sẽ thấy URL: `https://cubes2048-xxx.koyeb.app`

---

## Bước 4: Chơi game!

Copy URL ở trên → mở trình duyệt → bắt đầu chơi.

WebSocket tự động dùng `wss://` (HTTPS), không cần cấu hình gì thêm.

---

## Tối ưu bandwidth (đã làm sẵn trong server.js)

- ✅ Broadcast 20Hz → **10Hz** (giảm 50%)
- ✅ Nén WebSocket (**permessage-deflate**)
- ✅ Gzip HTML (giảm ~80% dung lượng)

Với 100 GB bandwidth, 5 người chơi cùng lúc chơi 2h/ngày → ~80 GB/tháng. OK trong ngưỡng free.

---

## Giữ server không bị sleep

Nếu có $5.5 credit, vào App Settings → chọn **"Always-on"** → server chạy 24/7.

Hoặc set `scaling.min: 1` trong `koyeb.yaml`.

---

## Lệnh hữu ích

```bash
# Cài Koyeb CLI
curl -fsSL https://cli.koyeb.com/install.sh | sh

# Login
koyeb login

# Xem log
koyeb logs cubes2048

# Deploy lại
koyeb deploy cubes2048

# Xem trạng thái
koyeb app list
```