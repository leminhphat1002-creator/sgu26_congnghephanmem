# Bát Tràng Audio Guide

Đồ án môn Công nghệ phần mềm: website giúp khách khám phá làng gốm Bát Tràng,
chọn địa điểm trên bản đồ và nghe thuyết minh bằng tiếng Việt, Anh hoặc Nhật.
Khách tham quan không cần tài khoản; người quản lý đăng nhập để biên tập dữ liệu.

Ứng dụng dùng **FastAPI, SQLAlchemy, SQLite, Leaflet và Piper TTS cục bộ**.
Môi trường phát triển, CI và bộ triển khai đều dành cho **Windows, Python 3.12 x64**.

## Chức năng chính

| Dành cho | Chức năng |
| --- | --- |
| Khách tham quan | Chọn quốc gia/khu vực tùy chọn và ngôn ngữ Việt/Anh/Nhật; ghi nhớ lựa chọn trên trình duyệt |
| Khách tham quan | Tìm địa điểm có/không dấu, chọn trên danh sách hoặc bản đồ, khám phá từ xa không cần GPS |
| Khách tham quan | Cấp quyền GPS để tìm điểm trong bán kính 500 m, hoặc dùng vị trí mẫu được ghi rõ |
| Khách tham quan | Đọc nội dung từ database, nhấn Play để nghe giọng đọc cục bộ; không tự phát âm thanh |
| Khách tham quan | Quét mã QR để mở website trên điện thoại |
| Người quản lý | Thêm/sửa/xóa địa điểm, cập nhật tọa độ và bật/tắt trạng thái hiển thị |
| Người quản lý | Biên tập riêng từng bài Việt/Anh/Nhật, tối đa 900 ký tự mỗi bài |
| Người quản lý | Xem dashboard: địa điểm, nội dung, yêu cầu thuyết minh, cache MP3 và lịch sử thao tác |
| Người quản lý | Xem khách đang hoạt động trong 2 phút gần nhất, tự cập nhật mỗi 15 giây |

Bộ dữ liệu mẫu có **5 địa điểm và 15 bài thuyết minh**: chợ gốm, đình làng, lò bầu cổ,
Bảo tàng Gốm và chùa Kim Trúc. Nguồn được ghi trong
[tệp nội dung](scripts/content/bat_trang_narrations.json) và
[hồ sơ xác minh](docs/bat-trang-data.md). Tọa độ là tham khảo từ nguồn trực tuyến,
chưa khảo sát thực địa hoặc xác nhận lối vào. Bản dịch cần rà soát trước khi sử dụng chính thức.

## Chạy lại trên máy đã cài đặt

Mở PowerShell tại thư mục repo. Chỉ tạo cấu hình nếu chưa có:

```powershell
if (-not (Test-Path -LiteralPath .\local.settings.json)) {
    Copy-Item -LiteralPath .\local.settings.example.json -Destination .\local.settings.json
}
.\scripts\run_local.ps1 -CheckOnly
.\scripts\run_local.ps1
```

| Trang | Địa chỉ mặc định |
| --- | --- |
| Khách tham quan | <http://localhost:8010/> |
| Quản lý | <http://localhost:8010/admin> |
| Mã QR | <http://localhost:8010/share> |
| Tài liệu API | <http://localhost:8010/docs> |
| Kiểm tra tiến trình | <http://localhost:8010/health> |

Giữ terminal mở khi sử dụng; **Ctrl+C** dừng website. Nếu cổng đang được dùng,
quay lại terminal chạy app cũ hoặc chọn cổng khác, ví dụ `-Port 8012`.
Launcher không tự dừng tiến trình có sẵn.

Launcher ưu tiên `.venv\py312\Scripts\python.exe`, sau đó `.venv\Scripts\python.exe`;
chỉ nhận Python 3.12 x64. Không cần activate venv. `-CheckOnly` kiểm tra cấu hình,
database và mô hình giọng đọc; không khởi động server hoặc kiểm tra cổng.
Xem thêm [hướng dẫn Windows](docs/local-windows.md).

### Mở trên điện thoại và tạo link Internet

Để tạo link HTTPS demo và QR tương ứng:

```powershell
.\scripts\run_local.ps1 -PublicDemo
```

Mở địa chỉ **QR page** được in trong terminal và quét mã mới. Chế độ này chạy app
riêng trên cổng **8011**, cùng Cloudflare Quick Tunnel; lần đầu tải công cụ tunnel
đã ghim phiên bản và xác minh SHA-256. Nếu cổng bận, dùng `-PublicDemo -Port 8012`.

**Máy tính, kết nối Internet và terminal phải duy trì hoạt động.** Khi tắt máy rồi
chạy lại, tunnel cấp URL mới; dùng QR mới. Link demo không phải tên miền cố định
hoặc hosting độc lập. Ctrl+C dừng app và tunnel do lệnh này tạo.

Nếu chỉ dùng cùng Wi-Fi, chạy `.\scripts\run_lan.ps1` và mở `/share` theo địa chỉ
LAN được in ra. Script không thay đổi firewall. Không dùng QR trỏ về `localhost`
trên điện thoại. GPS trên điện thoại cần HTTPS và quyền vị trí; HTTP LAN vẫn dùng
được chế độ khám phá từ xa. Xem [hướng dẫn demo](docs/FREE_HOSTING.md).

### Chuẩn bị âm thanh trước buổi demo

```powershell
.\scripts\run_local.ps1 -PrepareAudio
```

Lệnh tạo trước MP3 cho các bài đã xuất bản, bỏ qua bài đã có cache và không sửa database.
Chạy trước buổi demo để giảm thời gian chờ lượt nghe đầu tiên.

## Cài đặt trên máy mới

Cần Python **3.12 x64** và Internet để cài thư viện, tải mô hình. Tại thư mục repo:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m scripts.setup_offline_tts
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m scripts.seed_bat_trang
.\.venv\Scripts\python.exe -m scripts.create_admin --username admin --generate
if (-not (Test-Path -LiteralPath .\local.settings.json)) {
    Copy-Item -LiteralPath .\local.settings.example.json -Destination .\local.settings.json
}
.\scripts\run_local.ps1 -CheckOnly
.\scripts\run_local.ps1
```

Mật khẩu được tạo trong `data/admin-login.txt`, không có tài khoản/mật khẩu mặc định
trong source. Chỉ người có quyền chạy lệnh trên máy chủ mới tạo được tài khoản quản lý.

Các lệnh khởi tạo dùng đường dẫn mặc định và biến môi trường của terminal; không tự
đọc `local.settings.json`. Nếu dùng database hoặc thư mục mô hình riêng, đặt biến
môi trường tương ứng trước khi khởi tạo. Xem [cấu hình chi tiết](docs/local-windows.md).
Sao lưu database cũ trước khi chạy migration.

## Database và quản lý dữ liệu

Mặc định ứng dụng dùng **SQLite**, database là một file trên máy chạy website.
Không cần cài một dịch vụ database riêng để chạy bản local/demo.

| Đường dẫn mặc định | Nội dung |
| --- | --- |
| `data/app.db` | Địa điểm, bài thuyết minh, tài khoản, phiên đăng nhập và nhật ký hoạt động |
| `audio_files/` | File MP3 đã tạo, lưu riêng ngoài database |
| `tts_models/` | Mô hình giọng đọc Việt/Anh/Nhật |
| `data/backups/` | Bản sao lưu database và bản sao do các công cụ dữ liệu tạo |
| `data/logs/` | Log app/tunnel của chế độ demo công khai |
| `local.settings.json` | Cấu hình riêng: cổng, database, thư mục âm thanh, mô hình và URL QR |

Các đường dẫn này có thể đổi trong cấu hình. Launcher tính đường dẫn tương đối từ
thư mục repo; thứ tự ưu tiên là mặc định → JSON → biến môi trường → tham số lệnh.
Ứng dụng không tự nạp `.env`. Không commit cấu hình riêng, database, mật khẩu,
MP3, mô hình giọng đọc hoặc môi trường ảo. Không xóa các thư mục dữ liệu khi cập nhật mã.

### Chỉnh dữ liệu ở đâu?

Đăng nhập `/admin`, dùng **Địa điểm** để quản lý thông tin và trạng thái hiển thị;
dùng **Thuyết minh** để sửa từng bản ngôn ngữ. Địa điểm cần trạng thái sẵn sàng và
ít nhất một bài để xuất hiện trong catalog. Xóa địa điểm sẽ xóa các bài liên quan.

Các bảng chính gồm `locations`, `poi_narrations`, `admin_users`, `admin_sessions`,
`activity_events`, `app_settings` và `narration_cache` (cache nội dung của luồng cũ).
Trang admin hiện chưa có trình xem toàn bộ bảng, nút sao lưu hoặc nút dọn cache âm thanh.

Seed chạy lại không tạo trùng địa điểm và giữ nội dung đã biên tập. Khi nâng cấp dữ
liệu mẫu cũ, chỉ thay bài còn khớp hoàn toàn mẫu đã phát hành; có sao lưu SQLite
trước khi nâng cấp. Sửa bài đang dùng tại `/admin`; sửa JSON để đổi dữ liệu seed.

### Vì sao số MP3 có thể lớn hơn số bài?

Chỉ số **ÂM THANH ĐÃ LƯU** trên dashboard đếm tất cả file `*.mp3` trong `AUDIO_DIR`,
không phải số bài hiện tại. Khóa cache phụ thuộc văn bản, ngôn ngữ và giọng đọc.
Sửa bài hoặc đổi giọng tạo khóa mới; file cũ có thể vẫn còn. Nghe lại cùng nội dung,
ngôn ngữ và giọng dùng lại cache. Ví dụ 5 điểm × 3 ngôn ngữ có 15 bài, nhưng thư mục
có thể chứa 45 MP3 do còn các phiên bản khác.

Công cụ `cleanup_previous_project` là công cụ chuyển dữ liệu đồ án cũ, hiện chỉ
nhận khóa giọng Edge khi xác định MP3 cần giữ. Chưa dùng chế độ `--apply` để dọn
cache Piper hiện tại vì có thể xóa cả MP3 đang được sử dụng.

### Sao lưu database và quản lý tài khoản

Mở terminal khác tại thư mục repo. Chọn Python của môi trường đang dùng:

```powershell
$ProjectPython = if (Test-Path -LiteralPath .\.venv\py312\Scripts\python.exe) {
    '.\.venv\py312\Scripts\python.exe'
} else {
    '.\.venv\Scripts\python.exe'
}
& $ProjectPython -m scripts.database_snapshot backup truoc-khi-chinh-sua-01.db
```

Bản sao nằm trong `data/backups/`; mỗi lần dùng tên mới vì công cụ từ chối ghi đè.
Lệnh dùng SQLite backup API và kiểm tra tính toàn vẹn; không sao chép thô file DB
đang ghi. Bản sao này chỉ chứa database, không gồm MP3, mô hình hoặc cấu hình.
Nếu đổi `DATABASE_URL`, đặt biến môi trường tương ứng trước khi chạy các lệnh bảo trì;
các lệnh này không tự đọc JSON của launcher.

Đổi mật khẩu tài khoản đã có bằng prompt ẩn:

```powershell
& $ProjectPython -m scripts.create_admin --username admin --reset
```

Đổi mật khẩu thu hồi các phiên cũ. Mật khẩu trong database được băm PBKDF2-SHA256
với salt riêng, 600.000 vòng. Phiên có hạn 8 giờ; cookie HttpOnly, SameSite Strict,
Secure khi dùng HTTPS. API ghi dữ liệu yêu cầu phiên quản trị và token CSRF.

Dashboard đếm **yêu cầu thuyết minh**, không phải số khách duy nhất hoặc lượt nghe
hoàn tất; ngày thống kê dùng GMT+7. Bảng sự kiện không lưu tọa độ GPS, IP hoặc nội
dung bài; access log của server có thể chứa tham số URL, gồm tọa độ khi gọi API GPS.

Ô **KHÁCH ĐANG HOẠT ĐỘNG** đếm trình duyệt có tín hiệu trong 2 phút gần nhất.
Trang khách đang hiển thị gửi tín hiệu mỗi 30 giây; nhiều tab dùng chung cookie
được gộp. Đóng trang hoặc chuyển hết các tab khách xuống nền thì số giảm sau tối đa
2 phút không có tín hiệu, hiển thị ở nhịp cập nhật dashboard kế tiếp. Đây là ước
lượng theo trình duyệt, không xác minh từng người; trình duyệt/thiết bị khác tính
riêng. Trang quản lý không tự tính là khách. Số liệu nằm trong RAM của một process,
đặt lại khi restart; chưa hỗ trợ cộng gộp nhiều worker. Xem [chi tiết](docs/visitor-presence.md).

## Kiến trúc và API

Repo tổ chức theo modular monolith, tách API/schema, nghiệp vụ và truy cập dữ liệu.

```text
app/
  core/                 Cấu hình, database, xác thực, lỗi dùng chung
  modules/
    poi/                Địa điểm và tọa độ
    content/            Bài thuyết minh theo ngôn ngữ
    narration/          Điều phối chọn điểm, văn bản và giọng đọc
    audio/              Piper cục bộ, cache MP3 và luồng tương thích cũ
    admin/              Tài khoản, biên tập, dashboard
    sharing/            Link truy cập và mã QR
  static/               Giao diện khách, quản lý, Leaflet và bản đồ cục bộ
scripts/                Khởi tạo, chạy app, dữ liệu, giọng đọc và đóng gói
migrations/             Migration Alembic
tests/                 Kiểm thử backend và frontend
deploy/                Triển khai và phục hồi Windows
docs/                  Tài liệu kỹ thuật và hồ sơ đồ án
```

| API tiêu biểu | Mục đích |
| --- | --- |
| `GET /narration/catalog` | Catalog có nội dung, không cần GPS |
| `GET /narration/nearby?latitude=...&longitude=...` | Tìm điểm trong bán kính 500 m |
| `GET /narration/locations/{id}/text?language=vi` | Lấy bài từ database, không tạo âm thanh |
| `GET /narration/locations/{id}/speech?language=vi` | Phát Piper hoặc MP3 đã lưu |
| `GET /api/admin/dashboard` | Thống kê, yêu cầu đăng nhập quản lý |
| `GET /share/qr.png` | QR mở trang khách theo URL hiện tại |

Luồng khách hiện tại lấy văn bản trước, chỉ tạo/phát âm thanh khi nhấn Play. Bài
thiếu ngôn ngữ yêu cầu sẽ thử tiếng Anh rồi tiếng Việt và thông báo bản thay thế.
Piper chạy trên CPU máy chủ, gửi từng đoạn và chỉ lưu MP3 khi hoàn tất. Mô hình
được ghim checksum; setup tải mô hình, khách truy cập không kích hoạt tải mô hình.
Luồng cũ dùng Edge TTS/Wikimedia được giữ để tương thích, không phải luồng nghe mới.

Leaflet và nền vector GeoJSON vùng Bát Tràng được đóng gói cục bộ; không cần gọi
CDN hoặc máy chủ tile ngoài khi mở bản đồ. Giữ attribution nguồn trong giao diện.
Sau setup, nội dung/bản đồ/giọng đọc cục bộ vẫn cần máy khách kết nối tới server.
`/health` chỉ kiểm tra tiến trình phản hồi, không chứng minh DB và giọng đọc sẵn sàng.

## Kiểm thử, CI/CD và triển khai

Dùng `$ProjectPython` đã chọn ở phần bảo trì; frontend test cần Node.js (CI dùng Node 22):

```powershell
& $ProjectPython -m ruff check .
& $ProjectPython -m ruff format --check .
& $ProjectPython -m pytest --cov=app --cov-report=term-missing
node --test tests/frontend/i18n.test.cjs
node --test tests/frontend/presence.test.cjs
node --test tests/frontend/admin-presence.test.cjs
```

Kiểm tra tạo giọng thực tế bằng `& $ProjectPython -m scripts.check_offline_tts`.
Công cụ dùng cache tạm, chặn kết nối socket khi tạo giọng. Test PostgreSQL cần
`TEST_POSTGRES_URL` trỏ đến database kiểm thử riêng; không dùng database đang vận hành.

| Thành phần | Hành vi được cấu hình trong repo |
| --- | --- |
| [CI](.github/workflows/ci.yml) | Windows runner: Ruff, phân tích cú pháp PowerShell, pytest/coverage, frontend test, PostgreSQL native, build ZIP và smoke test gói thật |
| [CD: delivery](.github/workflows/cd.yml) | Sau CI thành công trên `main`, kiểm tra SHA/checksum và bàn giao đúng ZIP đã kiểm thử |
| CD: deploy-windows | Chỉ triển khai qua Windows OpenSSH khi `DEPLOY_ENABLED=true` và có cấu hình máy đích |
| Demo hiện tại | App trên máy Windows cá nhân, link HTTPS tạm qua tunnel; chưa có máy chủ production độc lập được kết nối |

Kết quả CI/CD phải xem tại **GitHub → Actions** theo commit tương ứng. Có workflow
trong repo không đồng nghĩa lần chạy mới nhất đã thành công hoặc đã triển khai server.
Gói bàn giao nằm tại **Actions → CD → Artifacts → `windows-release-<SHA>`**, gồm
`bat-trang-windows.zip` và checksum; artifact có thời hạn lưu theo workflow.

Bộ triển khai dùng Python 3.12 x64, dependency wheels, mô hình cục bộ và Windows
service qua WinSW khi chủ động cài đặt. Database/MP3 được giữ ngoài thư mục release
trên máy đích. Xem [triển khai Windows, secrets và rollback](docs/DEPLOYMENT.md).

## Tài liệu đồ án

| Tài liệu | Nội dung |
| --- | --- |
| [Bộ hồ sơ 5 file Word](docs/ho-so-do-an/README.md) | Đánh giá PRD, PRD hiệu chỉnh, phân tích thiết kế, kiểm thử và kịch bản demo |
| [Chạy Windows](docs/local-windows.md) | Cài đặt, cấu hình và chạy lại |
| [Demo HTTPS/LAN](docs/FREE_HOSTING.md) | Link Internet tạm, QR, yêu cầu duy trì máy |
| [Dữ liệu Bát Tràng](docs/bat-trang-data.md) | Nguồn nội dung và giới hạn tọa độ |
| [Ngôn ngữ khách](docs/visitor-language.md) | Chọn quốc gia, ngôn ngữ và nội dung thay thế |
| [Bản đồ cục bộ](docs/local-map.md) | Nguồn GeoJSON, phạm vi và attribution |
| [Giọng đọc cục bộ](docs/offline-tts.md) | Mô hình, giấy phép, setup và kiểm tra |
| [Triển khai Windows](docs/DEPLOYMENT.md) | Artifact, service, cấu hình và phục hồi |

Trước khi nộp, điền thông tin nhóm/giảng viên trong hồ sơ, thực hiện và ghi bằng
chứng các ca nghiệm thu thủ công trên thiết bị thật, rồi kiểm tra Actions của commit
được nộp. Các ca chưa làm và chỉ tiêu hiệu năng chưa đo phải giữ đúng trạng thái đó.
