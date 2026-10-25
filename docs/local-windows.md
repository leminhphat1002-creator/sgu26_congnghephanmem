# Chuẩn bị máy Windows trước khi tạo link

Chạy trong PowerShell tại thư mục repo, dùng Python 3.12 x64. Bước này chạy local
trên máy Windows, chưa tạo link Internet hoặc cài Windows service.

## Máy hiện tại

Database, tài khoản quản lý và mô hình giọng đọc đã được chuẩn bị. Tạo cấu hình một
lần nếu chưa có; không ghi đè file cấu hình đang dùng:

```powershell
if (-not (Test-Path -LiteralPath .\local.settings.json)) {
    Copy-Item -LiteralPath .\local.settings.example.json -Destination .\local.settings.json
}
.\scripts\run_local.ps1 -CheckOnly
.\scripts\run_local.ps1
```

Mở [trang khách](http://localhost:8010/), [quản lý](http://localhost:8010/admin)
và [trang QR](http://localhost:8010/share). Giữ terminal mở; Ctrl+C dừng website.
Nếu port đang dùng, dừng terminal chạy app cũ hoặc dùng `-Port 8011`.
Script không tự tắt tiến trình đang chiếm port.

Launcher ưu tiên `.venv\py312\Scripts\python.exe` của máy hiện tại, sau đó
`.venv\Scripts\python.exe`; chỉ nhận Python 3.12 x64. Có thể chỉ định
`-PythonPath 'C:\duong dan\venv\Scripts\python.exe'`.
Không cần activate venv hoặc dùng Python của Conda đang hiển thị ở dấu nhắc lệnh.

Trước buổi demo, tạo sẵn âm thanh cho các bài đã xuất bản:

```powershell
.\scripts\run_local.ps1 -PrepareAudio
```

Lệnh dùng cùng database, thư mục âm thanh và mô hình trong cấu hình. Bài có cache
được bỏ qua, bài sửa được tạo mới; không sửa nội dung hoặc tài khoản quản lý.

## Cấu hình được lưu

`local.settings.json` đã được bỏ qua bởi Git. Chỉ commit bản `example`.

| Khóa | Ý nghĩa |
| --- | --- |
| `PORT` | Cổng local, mặc định 8010 |
| `BIND_HOST` | Mặc định `127.0.0.1`, chỉ nghe trên máy hiện tại |
| `PUBLIC_BASE_URL` | Địa chỉ trang khách dùng cho QR; để trống khi chạy local |
| `DATABASE_URL` | SQLite mặc định `data/app.db`; có thể dùng PostgreSQL |
| `AUDIO_DIR` | MP3 được giữ trong `audio_files` |
| `PIPER_MODEL_DIR` | Mô hình được giữ trong `tts_models` |
| `TRUSTED_PROXY_IPS` | Proxy được tin cậy, mặc định chỉ `127.0.0.1` |

Đường dẫn dữ liệu tương đối luôn tính từ thư mục repo, kể cả khi gọi script từ
thư mục khác. Chuyển hoặc xóa thư mục repo cũng ảnh hưởng dữ liệu local; không xóa
`data`, `audio_files`, `tts_models` khi cập nhật mã. Đây là cấu hình phát triển/demo;
cấu hình Windows service độc lập vẫn dùng `settings.json` theo [DEPLOYMENT.md](DEPLOYMENT.md).

Thứ tự ưu tiên: mặc định → JSON → biến môi trường process → tham số lệnh.
Nếu đã đặt `$env:PUBLIC_BASE_URL` trong terminal cũ, có thể xóa bằng
`Remove-Item Env:PUBLIC_BASE_URL -ErrorAction SilentlyContinue` để dùng lại JSON.
Launcher không tự đọc `.env`.

`-CheckOnly` kiểm tra migration hiện tại, dữ liệu đã xuất bản, tài khoản quản lý và
checksum cả ba giọng đọc. Không seed, migrate hay tải mô hình. Kiểm tra này không
thay thế thử nghe thực tế; cổng chỉ được kiểm tra khi khởi chạy server.

## Trên máy mới chưa cài

Cài Python 3.12 x64, rồi chạy từ repo:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m scripts.setup_offline_tts
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m scripts.seed_bat_trang
.\.venv\Scripts\python.exe -m scripts.create_admin --username admin --generate
Copy-Item -LiteralPath .\local.settings.example.json -Destination .\local.settings.json
.\scripts\run_local.ps1 -CheckOnly
.\scripts\run_local.ps1
```

Giữ mật khẩu được tạo ở nơi riêng, không commit. Các lệnh khởi tạo trên dùng đường
dẫn mặc định và biến môi trường hiện tại. Nếu cấu hình database/thư mục mô hình riêng,
đặt biến môi trường tương ứng cho lệnh khởi tạo; lệnh setup mô hình nhận thêm
`--directory 'duong-dan-mo-hinh'`. Sao lưu DB trước khi chạy migration trên dữ liệu cũ.

## Sau này khi có link HTTPS

Để `BIND_HOST` là `127.0.0.1` nếu dùng tunnel trên cùng máy. Đổi
`PUBLIC_BASE_URL` trong JSON thành địa chỉ HTTPS thật (không chứa `/admin`), dừng app
bằng Ctrl+C rồi chạy lại `run_local.ps1`. Trang `/share` sẽ tạo QR theo địa chỉ đó.
Đặt URL chỉ đổi nội dung QR, không tự cấp tên miền hay công khai website.
Các bước tạo link riêng ở [FREE_HOSTING.md](FREE_HOSTING.md).

Để tạo link HTTPS demo tự động, dùng `.\scripts\run_local.ps1 -PublicDemo`.
Lệnh dùng app riêng ở cổng 8011 và tự gắn URL thật vào QR; cần Internet và giữ
terminal mở. Cấu hình local ở 8010 được giữ nguyên.

QR local hiện tại dùng để xem trước; điện thoại không truy cập máy bạn bằng localhost.
Máy chủ vẫn phải bật khi demo. Nếu muốn chạy độc lập, cần máy Windows được phép chạy
liên tục và cấu hình service ở bước triển khai.
