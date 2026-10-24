# Bát Tràng Audio Guide

Ứng dụng thuyết minh đa ngôn ngữ dùng FastAPI, SQLite, GPS và Edge TTS.
Giữ kiến trúc modular monolith 3 lớp: API/schema → service → repository/client/store.

## Chức năng

- **Khám phá từ xa:** xem danh sách và chọn nghe mà không cần cấp GPS.
- **Tham quan tại chỗ:** tìm địa điểm đã lưu trong bán kính 500 m, gần nhất trước.
- **Vị trí mẫu:** mô phỏng tọa độ tại Bát Tràng, hiển thị rõ khác với GPS thiết bị.
- Nội dung Việt, Anh, Nhật lưu lâu dài trong `poi_narrations`, khóa theo địa điểm/ngôn ngữ.
- Thiếu bản ngôn ngữ yêu cầu: thử tiếng Anh rồi tiếng Việt, thông báo bản thay thế.
- Edge TTS tạo MP3 và cache; nếu TTS lỗi vẫn hiển thị văn bản. Người dùng nhấn Play để nghe.

Luồng sử dụng mới không gọi Wikipedia để tìm POI hoặc lấy nội dung. Client Wikimedia cũ
và các API quản lý cache cũ được giữ để tham khảo/tương thích; không tham gia luồng thuyết minh.
Xóa cache cũ không xóa các bài biên soạn trong `poi_narrations`.

## Chạy local (PowerShell)

Khuyến nghị Python 3.12 x64. Máy phát triển, CI và đích triển khai đều dùng Windows;
không cần Docker, WSL hoặc Bash.

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
.\.venv\Scripts\python -m alembic upgrade head
.\.venv\Scripts\python -m scripts.seed_bat_trang
.\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

Mở http://localhost:8000, API docs tại `/docs`, health check tại `/health`.
Ứng dụng đọc biến môi trường của process; không tự nạp `.env` khi chạy uvicorn.
Ví dụ đổi database: `$env:DATABASE_URL = "sqlite:///./data/demo.db"` trước các lệnh trên.
Không cần cấu hình Wikimedia cho ứng dụng mới.

Migration mới chỉ thêm bảng, không sửa migration cũ hoặc xóa dữ liệu hiện có.
Seed chạy lặp không tạo trùng và không ghi đè bài đã biên tập. Dữ liệu đang sử dụng chỉ giữ các điểm Bát Tràng;
catalog từ xa liệt kê địa điểm sẵn sàng có bài trong `poi_narrations`.

**Dữ liệu demo:** 5 điểm, 15 bài mẫu, tọa độ minh họa quanh Bát Tràng; chưa phải dữ liệu
khảo sát hay nội dung chính thức. Hai điểm trưng bày/trải nghiệm là điểm giả định phục vụ demo.
Cần xác minh tên, tọa độ, thông tin lịch sử và bản dịch trước khi dùng ngoài thực tế.
Chỉnh dữ liệu mẫu trong `scripts/seed_bat_trang.py` trước lần seed đầu tiên; với DB đã seed,
biên tập trực tiếp bảng `poi_narrations` và `locations`, vì seed không ghi đè dữ liệu.

## API chính

| API | Mục đích |
| --- | --- |
| `GET /narration/catalog` | Danh sách có bài thuyết minh, không cần GPS |
| `GET /narration/nearby?latitude=...&longitude=...` | POI SQLite trong 500 m |
| `POST /narration/locations/{id}?language=vi` | Thuyết minh theo lựa chọn, không cần GPS |
| `POST /narration/detect` | Chọn POI trong bán kính kích hoạt (mặc định 80 m) |
| `GET /content?title=...&lang=vi` | Đọc nội dung SQLite theo tên |
| `GET /locations` | Quản lý/danh sách địa điểm hiện có |
| `GET /audio/{filename}` | Phát MP3 đã tạo |

GPS thiết bị cần quyền vị trí và HTTPS hoặc localhost. Chế độ mô phỏng không giả mạo GPS
thiết bị. Đọc bài từ database không cần Internet; tạo MP3 mới vẫn cần kết nối tới Edge TTS.

## Kiểm thử và CI

```powershell
.\.venv\Scripts\python -m pytest --cov=app --cov-report=term-missing
.\.venv\Scripts\python -m ruff check .
.\.venv\Scripts\python -m ruff format --check .
```

CI dùng runner Windows, PowerShell, Ruff, pytest/coverage và PostgreSQL native.
Build tạo ZIP gồm source và dependency wheels; smoke test cài offline vào venv mới rồi
chạy app Windows thật. CD bàn giao đúng ZIP đã qua CI, có thể triển khai qua Windows
OpenSSH đến service Windows khi bật `DEPLOY_ENABLED`. Chưa có máy chủ đích được kết nối.
Chi tiết artifact, service, secrets và phục hồi tại [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).
Demo không thuê server bằng máy Windows tại [docs/FREE_HOSTING.md](docs/FREE_HOSTING.md).
SQLite dùng cho local và triển khai Windows mặc định; PostgreSQL vẫn được hỗ trợ tùy chọn.
Test dùng database tạm và giả lập TTS. Job PostgreSQL kiểm tra DB native trên GitHub.

## Gói phát hành Windows

Tải `windows-release-<SHA>` từ **Actions → CD → Artifacts** sau khi CI thành công.
Gói `bat-trang-windows.zip` chạy với Python 3.12 x64 trên Windows, kèm manifest SHA256
và wheelhouse để cài offline. Không có Docker image hoặc bước phát hành GHCR.
Database/MP3 được lưu ngoài thư mục release trên máy đích. Dùng WinSW để chạy app như
Windows service; script chỉ cài khi bạn chủ động chạy theo tài liệu triển khai.
Không commit `.env`, database, MP3, môi trường ảo hoặc file mật khẩu. Mã và seed có thể commit.

## Quản trị và mã QR

Khách vào trang `/` hoặc quét QR để khám phá, không cần đăng nhập. Trang `/admin` dành
cho người quản lý; các API thêm/sửa/xóa địa điểm, nội dung và xóa cache yêu cầu phiên
quản trị cùng token CSRF. Không có tài khoản/mật khẩu mặc định được đưa vào source code.

Sau khi cài dependencies và chạy migration, tạo tài khoản:

```powershell
.\.venv\Scripts\python -m scripts.create_admin --username admin --generate
```

Lệnh tạo mật khẩu ngẫu nhiên trong `data/admin-login.txt` (Git bỏ qua). Mở file để lấy
thông tin đăng nhập. Có thể tự đặt mật khẩu qua prompt ẩn bằng cách bỏ `--generate`.
Đổi mật khẩu qua `python -m scripts.create_admin --username admin --reset`; các phiên cũ
sẽ bị thu hồi. Chỉ người có quyền chạy lệnh trên máy chủ mới tạo được tài khoản quản lý.
Phiên có hạn 8 giờ, cookie HttpOnly/SameSite Strict, Secure khi dùng HTTPS. Mật khẩu trong DB
được băm PBKDF2-SHA256 với salt riêng, 600.000 vòng; file chứa mật khẩu ban đầu chỉ dành cho
chủ máy, có thể xóa sau khi đã lưu mật khẩu ở nơi phù hợp.

Dashboard có tổng địa điểm, số địa điểm có bài được hiển thị, số bài theo ngôn ngữ,
lượt yêu cầu thuyết minh hôm nay và 7 ngày, dung lượng MP3, lịch sử thao tác. Lượt yêu cầu
không đồng nghĩa số người nghe hoặc số lần phát hoàn tất. Mốc ngày dùng GMT+7.
Thống kê bắt đầu từ khi thêm tính năng này, không suy đoán dữ liệu các lần dùng trước.
Các sự kiện không lưu GPS, IP hoặc nội dung bài; bộ giới hạn đăng nhập dùng IP trong bộ nhớ
một process (5 lần/phút), không phải cơ chế phân tán.

Mục **Địa điểm** cho phép thêm/sửa/xóa, bật/tắt hiển thị; mục **Thuyết minh** lưu riêng từng
bản Việt/Anh/Nhật (tối đa 900 ký tự mỗi bài). Tên và mô tả được hiển thị dưới dạng văn bản,
không thực thi HTML. Xóa địa điểm sẽ xóa các bài liên quan. Nội dung mới tạo khóa MP3 mới;
các MP3 cũ có thể vẫn còn trong cache. AudioService dùng đúng thư mục `AUDIO_DIR`.

### Quét QR từ điện thoại trên cùng mạng

```powershell
.\scripts\run_lan.ps1
```

Script lấy địa chỉ LAN đang có default gateway, đặt `PUBLIC_BASE_URL`, rồi chạy server
trên cổng 8010 và in địa chỉ. Giữ terminal mở. Điện thoại và máy chủ cần cùng Wi-Fi, cổng
phải truy cập được theo cấu hình firewall hiện có. Script không thay đổi firewall.
Trong trường hợp nhiều card mạng, chỉ định đường dẫn phù hợp:

```powershell
.\scripts\run_lan.ps1 -Port 8010 -PublicUrl "http://192.168.1.10:8010"
```

Đây là liên kết trong mạng nội bộ; chưa phải triển khai Internet. GPS trên điện thoại
cần HTTPS; khám phá từ xa và nghe theo lựa chọn vẫn dùng được trên HTTP LAN.
Mở `/share` để xem, tải PNG hoặc in QR. SVG tại `/share/qr.svg`, PNG tại `/share/qr.png`.
QR được tạo trên server, không chứa mật khẩu/tài khoản và không gửi link qua dịch vụ QR khác.
Đổi IP hoặc tên miền cần tải lại QR; không in QR trỏ về `localhost` để dùng trên điện thoại.

Khi có tên miền công khai, đặt `PUBLIC_BASE_URL=https://ten-mien-cua-ban` trong biến môi trường
của server Windows và chạy qua HTTPS. `uvicorn` không tự nạp `.env`. Với Windows service,
chỉnh `C:\BatTrang\settings.json` rồi restart service; tạo admin trên DB máy đích theo
[hướng dẫn triển khai](docs/DEPLOYMENT.md).

Tham khảo kỹ thuật: [qrcode](https://pypi.org/project/qrcode/8.2/),
[OWASP Password Storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html).


## Dọn dữ liệu đồ án cũ

`scripts/seed_poi.py` đã chuyển sang seed Bát Tràng, không thêm lại địa điểm TP.HCM.
Database local đã dọn các địa điểm đồ án cũ, cache nội dung và MP3 không còn được dùng
bởi bài thuyết minh hiện tại. Tài khoản, phiên quản trị và nội dung Bát Tràng được giữ nguyên.

Để áp dụng cùng thao tác trên database cũ khác, xem trước rồi chạy:

```powershell
python -m scripts.cleanup_previous_project
python -m scripts.cleanup_previous_project --apply
```

Script chỉ xóa danh sách địa điểm cũ đã nhận diện trong `LEGACY_NAMES`. Các file MP3
có khóa hợp lệ nhưng không còn khớp nội dung hiện tại cũng được dọn. Trước khi xóa,
script sao lưu DB và MP3 vào `data/backups/previous-project-...`, kèm `manifest.json`
ghi đường dẫn gốc để phục hồi nếu cần. Bản sao lưu không được phục vụ trên website.
