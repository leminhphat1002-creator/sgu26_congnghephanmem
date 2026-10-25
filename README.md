# Bát Tràng Audio Guide

Ứng dụng thuyết minh đa ngôn ngữ dùng FastAPI, SQLite, GPS và Piper TTS cục bộ.
Giữ kiến trúc modular monolith 3 lớp: API/schema → service → repository/client/store.

## Chức năng

- **Ngôn ngữ cho khách:** lần đầu mở trang sẽ hỏi quốc gia/khu vực (tùy chọn)
  và ngôn ngữ Việt/Anh/Nhật. Đổi cả giao diện và thuyết minh, ghi nhớ riêng
  trên trình duyệt; nút Language ở đầu trang cho phép đổi lại. Xem [chi tiết](docs/visitor-language.md).
- **Khám phá từ xa:** xem danh sách và chọn nghe mà không cần cấp GPS.
- **Bản đồ tương tác:** chọn điểm đánh dấu ở Bát Tràng để tải thuyết minh; lựa chọn đồng bộ
  với danh sách và ngôn ngữ Việt/Anh/Nhật. Có nút xem tất cả điểm và liên kết tới bài đã chọn.
- Tìm tên địa điểm có/không dấu, lọc chung trên bản đồ và danh sách. Chọn điểm sẽ hiện ngay
  khung bài đang tải; đổi ngôn ngữ tự tải bản mới cho chính điểm đó. Bấm lại cùng điểm/ngôn
  ngữ không gửi thêm yêu cầu hoặc đặt lại MP3; có nút thử lại nếu tải lỗi/chưa có âm thanh.
  Nút Xem tất cả điểm bỏ bộ lọc, mở toàn bộ catalog Bát Tràng và căn lại bản đồ, kể cả khi
  vị trí tìm kiếm hiện tại không có điểm nào.
- Cập nhật vị trí giữ bài và âm thanh nếu điểm còn trong kết quả, cập nhật khoảng cách,
  gợi ý điểm gần nhất trong danh sách. Không tự chọn điểm hoặc tự phát âm thanh.
- **Tham quan tại chỗ:** tìm địa điểm đã lưu trong bán kính 500 m, gần nhất trước.
- **Vị trí mẫu:** mô phỏng tọa độ tại Bát Tràng, hiển thị rõ khác với GPS thiết bị.
- Nội dung Việt, Anh, Nhật lưu lâu dài trong `poi_narrations`, khóa theo địa điểm/ngôn ngữ.
- Thiếu bản ngôn ngữ yêu cầu: thử tiếng Anh rồi tiếng Việt, thông báo bản thay thế.
- Piper tạo giọng đọc cục bộ và cache; văn bản hiển thị ngay. Người dùng nhấn Play để nghe.

Luồng sử dụng mới không gọi Wikipedia để tìm POI hoặc lấy nội dung. Client Wikimedia cũ
và các API quản lý cache cũ được giữ để tham khảo/tương thích; không tham gia luồng thuyết minh.
Xóa cache cũ không xóa các bài biên soạn trong `poi_narrations`.

## Chạy local (PowerShell)

Khuyến nghị Python 3.12 x64. Máy phát triển, CI và đích triển khai đều dùng Windows;
không cần Docker, WSL hoặc Bash.

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
.\.venv\Scripts\python -m scripts.setup_offline_tts
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

**Nội dung Bát Tràng:** 5 điểm, 15 bài biên soạn bằng tiếng Việt, Anh và Nhật, có nguồn
tham khảo cho từng điểm trong [tệp nội dung](scripts/content/bat_trang_narrations.json).
Bài viết phục vụ đồ án, không phải nội dung chính thức của đơn vị quản lý di tích.
Tọa độ vẫn là minh họa chưa khảo sát; hai điểm trưng bày/trải nghiệm là điểm chủ đề,
không phải vị trí đã xác minh của bảo tàng hoặc một xưởng cụ thể.

Để đưa bài mới vào DB cũ, chạy lại `python -m scripts.seed_bat_trang`.
Lệnh tạo bản sao SQLite trong `data/backups/`, thêm bài còn thiếu và chỉ thay những bài
khớp hoàn toàn với mẫu cũ (kiểm tra cả tiêu đề và nội dung). Các bài đã tự biên tập,
tọa độ, tài khoản và phiên quản trị được giữ lại. Bản sao DB không được commit.
Sửa bài đang sử dụng tại trang quản lý; sửa tệp JSON nếu muốn đổi nội dung cho DB mới.
Nguồn được kiểm tra ngày 25/10/2026; bản dịch cần được rà soát trước khi dùng chính thức.

## API chính

Trang người dùng lấy văn bản ngay, sau đó nhấn Play để nghe **Piper chạy trên CPU máy chủ**.
Âm thanh được gửi từng đoạn khi tạo ra, không chờ tạo toàn bài hoặc gọi dịch vụ giọng đọc
qua Internet. Bài hoàn tất được lưu để lần sau phát từ file; bài sửa có khóa cache mới.
Chỉ tự tải mô hình trong lệnh setup, không tải khi khách truy cập. Mô hình khoảng 204 MB,
được ghim revision và SHA-256 trong `app/modules/audio/offline_voices.json`.

Chạy `python -m scripts.check_offline_tts` để thử cả ba ngôn ngữ với socket bị chặn và cache
trống. Trước buổi demo, chạy `python -m scripts.prepare_narration_audio` để tạo trước toàn bộ
bài đang dùng. Giọng thiết bị vẫn là lựa chọn phụ nếu máy có giọng đúng ngôn ngữ. Giọng đọc
cục bộ có âm sắc khác Edge TTS; máy chủ phải hoạt động và cài đủ mô hình/thư viện.

CI/CD Windows tải và kiểm tra mô hình lúc build, đóng gói mô hình cùng dependency wheels;
smoke test của ZIP kiểm tra tạo giọng khi bị chặn mạng. File mô hình và MP3 không commit.
Có thể đổi thư mục mô hình bằng `PIPER_MODEL_DIR` và `setup_offline_tts --directory ...`.
Thông tin nguồn và giấy phép ở [docs/offline-tts.md](docs/offline-tts.md).

| API | Mục đích |
| --- | --- |
| `GET /narration/catalog` | Danh sách có bài thuyết minh, không cần GPS |
| `GET /narration/locations/{id}/text?language=vi` | Bài viết trả ngay từ DB, không gọi TTS |
| `GET /narration/locations/{id}/speech?language=vi` | Phát từng đoạn từ Piper cục bộ; file cache hỗ trợ tua |
| `GET /narration/nearby?latitude=...&longitude=...` | POI SQLite trong 500 m |
| `POST /narration/locations/{id}?language=vi` | Thuyết minh theo lựa chọn, không cần GPS |
| `POST /narration/detect` | Chọn POI trong bán kính kích hoạt (mặc định 80 m) |
| `GET /content?title=...&lang=vi` | Đọc nội dung SQLite theo tên |
| `GET /locations` | Quản lý/danh sách địa điểm hiện có |
| `GET /audio/{filename}` | Phát MP3 đã tạo |

GPS thiết bị cần quyền vị trí và HTTPS hoặc localhost. Chế độ mô phỏng không giả mạo GPS
thiết bị. Đọc và tạo giọng mới không cần Internet sau khi setup. Máy khách vẫn cần kết nối
tới máy chủ. Các API POST tạo MP3 cũ dùng Edge TTS được giữ để tương thích, không dùng trong
luồng nghe mới của trang người dùng.

Bản đồ dùng Leaflet 1.9.4 lưu cục bộ ở `app/static/vendor/leaflet`, kèm giấy phép BSD-2-Clause;
không tải thư viện JavaScript từ CDN lúc mở trang. Nền OpenStreetMap cần Internet và giữ
attribution trên bản đồ. Không tải trước hoặc lưu offline hàng loạt các ô bản đồ. Khi nền
bản đồ lỗi, vẫn chọn được marker hoặc dùng danh sách. Điểm thiếu tọa độ không có marker
nhưng vẫn chọn được trong danh sách. Chỉ vẽ các điểm của catalog/phạm vi tìm kiếm hiện tại;
không tự xin quyền GPS hoặc tra cứu địa điểm từ bên thứ ba.
Tham khảo [Leaflet](https://leafletjs.com/examples/quick-start/) và
[OpenStreetMap tile policy](https://operations.osmfoundation.org/policies/tiles/).

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
