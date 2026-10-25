# Demo không thuê server, chạy ứng dụng trên Windows

Theo lựa chọn Windows toàn bộ, phương án Render + Neon và Docker image đã được thay
bằng CI Windows và gói ZIP. Chưa có tài khoản hosting/server mới được tạo hoặc kết nối.

## Có thể làm ngay với máy hiện tại

Dùng máy Windows sẵn có để chạy app, SQLite và MP3. Không cần thuê VPS để demo.
Máy phải bật, không sleep, có mạng; tắt máy hoặc dừng tiến trình thì website ngừng phục vụ.
Đây là demo từ máy cá nhân, chưa phải hosting độc lập chạy khi tắt máy.

Chuẩn bị và kiểm tra máy trước theo [local-windows.md](local-windows.md).
Launcher dùng `local.settings.json` riêng; giữ cấu hình này khi chạy lại.

### Demo cùng Wi-Fi

```powershell
.\scripts\run_lan.ps1
```

Quét QR tại `/share` bằng điện thoại cùng mạng. HTTP LAN không đủ điều kiện GPS của
trình duyệt điện thoại; khám phá từ xa vẫn dùng được. Script không tự mở firewall.

### Demo Internet qua HTTPS

Cách chạy gọn trên Windows:

```powershell
.\scripts\run_local.ps1 -PublicDemo
```

Script kiểm tra dữ liệu/giọng đọc, tải `cloudflared` Windows 2026.10.3 từ release
chính thức và xác minh SHA-256 lần đầu (khoảng 55 MB). Binary được lưu trong
`data/tools`, không cài service, không cần quyền admin và không commit vào Git.
Nguồn release: [Cloudflare 2026.10.3](https://github.com/cloudflare/cloudflared/releases/tag/2026.10.3).

Chế độ này dùng cổng **8011** và chỉ bind `127.0.0.1`; bản LAN ở 8010 có thể tiếp tục
chạy. Script tạo tunnel HTTP/2, lấy URL HTTPS thật rồi khởi động app với QR trỏ đúng
URL đó, không sửa `local.settings.json`. Mở **QR page** HTTPS được in trong terminal
và quét mã mới. Điện thoại có thể dùng Wi-Fi khác hoặc 4G/5G.

Giữ terminal mở; Ctrl+C dừng cả app và tunnel do lệnh này tạo. Mỗi lần chạy lại có
URL và QR mới. Nếu cổng 8011 đang dùng, dừng phiên demo cũ ở terminal đã mở nó hoặc
chọn `-PublicDemo -Port 8012`; script không dừng tiến trình có sẵn.
Log chẩn đoán nằm trong `data/logs/tunnel-*.log` và `public-app-*.log`.
Khi không kết nối được Cloudflare, script báo lỗi và dọn tiến trình của nó;
website LAN vẫn chạy. Không tắt firewall hoặc bỏ kiểm tra TLS.

Tài nguyên tĩnh, gồm nền bản đồ GeoJSON, được nén gzip nếu trình duyệt hỗ trợ để giảm
dữ liệu truyền qua Wi-Fi/Internet. Nén chỉ áp dụng cho `/static`, không áp dụng cho
API hoặc luồng âm thanh. Tốc độ thực tế còn phụ thuộc mạng của máy và điện thoại.

Nếu muốn tự chạy từng terminal, dùng các bước thủ công dưới đây.

Dùng binary `cloudflared.exe` dành cho Windows từ
[nguồn chính thức](https://developers.cloudflare.com/tunnel/downloads/).
Cloudflare Quick Tunnel cấp URL tạm `trycloudflare.com`, không cần tài khoản/tên miền;
chỉ dành cho thử nghiệm, URL đổi mỗi lần chạy và không có cam kết uptime.
Xem [giới hạn Quick Tunnels](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/).

Mở terminal thứ nhất và chạy:

```powershell
.\scripts\run_local.ps1 -BindHost 127.0.0.1 -Port 8010
```

Terminal thứ hai:

```powershell
C:\Tools\cloudflared.exe tunnel --url http://127.0.0.1:8010
```

Lấy URL HTTPS được in ra. Dừng app ở terminal thứ nhất bằng Ctrl+C rồi chạy lại với URL đó:

```powershell
.\scripts\run_local.ps1 -BindHost 127.0.0.1 -Port 8010 -PublicUrl 'https://URL-THAT-CUA-BAN.trycloudflare.com'
```

Giữ cả hai terminal mở; truy cập URL HTTPS trên điện thoại, mở `/share` để tải QR mới.
Ai có URL đều truy cập được phần khách; trang quản lý vẫn cần đăng nhập.
GPS cần người dùng cho phép và phụ thuộc thiết bị. Không dùng URL mẫu trong QR thật.
Muốn giữ URL cho lần chạy sau, điền `PUBLIC_BASE_URL` trong `local.settings.json`;
tham số `-PublicUrl` chỉ có hiệu lực cho lần chạy hiện tại. Khi tunnel đổi URL, cập nhật lại.

## Khi cần máy đích chạy độc lập

Cần một máy Windows khác được phép chạy liên tục, ví dụ máy của nhóm/trường được cấp
quyền sử dụng, hoặc Windows server của nhà cung cấp bạn chọn. Chưa chọn dịch vụ cloud
Windows miễn phí hoặc tạo tài nguyên có phí. Không coi GitHub Actions là nơi host website.

CI/CD đã chuẩn bị bàn giao ZIP và triển khai đến Windows qua OpenSSH khi có máy đích.
Hướng dẫn service, dữ liệu bền vững, HTTPS và GitHub settings ở [DEPLOYMENT.md](DEPLOYMENT.md).
Quick Tunnel HTTP không giúp GitHub truy cập SSH vào máy nằm sau NAT; chưa có kết nối
SSH thật thì giữ `DEPLOY_ENABLED` trống/false và triển khai thủ công khi cần demo.

## Cách trình bày trong báo cáo

- Đã có: mã CI/CD chạy trên Windows, artifact ZIP và script cập nhật/rollback Windows.
- Cần bằng chứng sau khi push: CI thành công, smoke test ZIP thành công, artifact tải được.
- Chỉ ghi đã deploy tự động khi job deploy thực sự chạy đến máy đích và xác minh đúng SHA.
- Demo bằng tunnel cần nêu rõ máy phải bật và URL tạm thời; giữ bản local để dự phòng.
