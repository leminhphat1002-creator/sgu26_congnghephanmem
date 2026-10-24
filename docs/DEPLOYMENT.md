# CI/CD trên Windows

## Luồng phát hành

Máy phát triển, GitHub Actions và máy triển khai đều chạy Windows x64 / Python 3.12.
Không cần WSL, Bash, Docker hoặc container. Các lệnh workflow dùng PowerShell.

1. CI chạy Ruff, pytest/coverage và PostgreSQL native của runner `windows-2025`.
2. CI tạo `bat-trang-windows.zip`, gồm source theo danh sách cho phép, migration,
   deployment tools và toàn bộ dependency wheels được tải trong chính lần build đó.
3. CI giải nén vào thư mục tạm, cài offline trong venv mới và chạy app thật để kiểm tra
   migration, seed lặp, catalog 5 điểm, giao diện, QR, quyền quản trị và revision header.
4. CI lưu đúng ZIP đã kiểm tra thành artifact `windows-package-<SHA>` trong 7 ngày.
5. CD chỉ nhận CI thành công từ push/chạy thủ công trên `main`, cùng repository;
   không nhận CI của PR/fork. CD kiểm tra SHA256 và manifest rồi phát hành artifact
   `windows-release-<SHA>` trong 30 ngày. Không build lại hoặc tải lại dependencies.
6. Nếu `DEPLOY_ENABLED` chưa bằng `true`, dừng ở bước bàn giao gói; không liên hệ server.
7. Khi có máy Windows đích, CD dùng OpenSSH Windows để gửi ZIP và chạy deployment tools.

Tải ZIP tại **Actions → CD → lần chạy thành công → Artifacts**. Giải nén artifact của
GitHub trước; ZIP ứng dụng bên trong là `bat-trang-windows.zip`.
Nếu artifact hết hạn, chạy lại **Actions → CI → Run workflow → main**.

## Chuẩn bị máy Windows đích khi đã có

Chưa có máy chủ được kết nối. Các hướng dẫn dưới đây không tự cài dịch vụ hoặc mở cổng
trên máy cá nhân. Có thể triển khai thủ công trên Windows để demo trước khi bật CD từ xa.

Cần:

- Windows 10/11 hoặc Windows Server có Python **3.12 x64 cài cho tất cả người dùng**,
  đường dẫn cố định, ví dụ `C:\Python312\python.exe`; không dùng Python trong venv của repo.
- Thư mục riêng `C:\BatTrang`; dữ liệu runtime không nằm trong Git checkout.
- WinSW **2.12.0 x64** lấy từ [bản phát hành chính thức](https://github.com/winsw/winsw/releases/tag/v2.12.0).
  Tải và xác minh binary theo nguồn phát hành trước khi cung cấp đường dẫn cho script.
- Với CD từ GitHub: OpenSSH Server trên Windows, tài khoản SSH có quyền triển khai vào
  thư mục này và điều khiển service, public key riêng, host key đã xác minh. SSH phải
  truy cập được từ GitHub runner. Tunnel HTTP cho website không cung cấp kết nối SSH này.
- Với website công khai: HTTPS qua reverse proxy chạy trên Windows hoặc HTTP tunnel.
  Mặc định app chỉ bind `127.0.0.1`; script không tự mở firewall/DNS.

Trong PowerShell **Administrator**, từ source code đã kiểm tra:

```powershell
.\deploy\install_service.ps1 -Root C:\BatTrang -PythonPath C:\Python312\python.exe -WinSwPath C:\Tools\WinSW-x64.exe
```

Script cài service `BatTrangGuide` bằng WinSW, chạy với tài khoản LocalService, chưa start.
Source chỉ có script cấu hình, không chứa binary WinSW. LocalService đọc code và chỉ
được cấp quyền sửa thư mục `data`, `audio_files`, `logs`. Python nền phải cho LocalService
quyền đọc/chạy. Không trỏ `Root` vào thư mục chứa dữ liệu không liên quan.

Chỉnh `C:\BatTrang\settings.json` (script tạo từ `deploy/settings.example.json`):

```json
{
  "PUBLIC_BASE_URL": "http://localhost:8010",
  "PORT": 8010,
  "BIND_HOST": "127.0.0.1",
  "TRUSTED_PROXY_IPS": "127.0.0.1"
}
```

`http://localhost:8010` dùng cho triển khai thử trên máy đích. Khi công khai, đặt
`PUBLIC_BASE_URL` thành origin HTTPS thật. `TRUSTED_PROXY_IPS` chỉ gồm địa chỉ proxy
đáng tin cậy, không đặt `*`. URL trong settings quyết định QR và probe triển khai;
repository variable chỉ tạo liên kết hiển thị trong Actions.

## Triển khai thủ công lần đầu

Giữ source deployment tools và ZIP bên ngoài thư mục runtime. Trong PowerShell Admin,
từ checkout đúng commit của ZIP (thay SHA mẫu bằng SHA thật của artifact):

```powershell
$revision = "SHA_40_KY_TU_CUA_GOI"
C:\Python312\python.exe -m deploy.windows_deploy --archive C:\Downloads\bat-trang-windows.zip --root C:\BatTrang --revision $revision --sequence 1
```

Mỗi release có venv riêng, cài offline từ wheelhouse. SQLite nằm ở
`C:\BatTrang\data\app.db`, MP3 ở `C:\BatTrang\audio_files`, không bị ghi đè bởi ZIP.
Chỉ DB chưa tồn tại mới seed 5 POI/15 bài mẫu. Tài khoản local không tự upload.

Sau lần đầu, tạo admin bằng prompt ẩn trong terminal trên máy đích:

```powershell
$root = 'C:\BatTrang'
$state = Get-Content -LiteralPath "$root\current-release.json" -Raw | ConvertFrom-Json
$release = Join-Path $root $state.release
$env:DATABASE_URL = 'sqlite:///C:/BatTrang/data/app.db'
Push-Location -LiteralPath $release
try { & "$release\.venv\Scripts\python.exe" -m scripts.create_admin --username admin }
finally { Pop-Location }
```

Không dùng `--generate` ở release để tránh ghi file mật khẩu trong thư mục code.
Các bài đã sửa, địa điểm đã xóa và mật khẩu được giữ trong DB qua lần cập nhật.

## Bật CD từ GitHub

Chỉ bật sau khi triển khai thủ công, Windows service và kết nối SSH đã chạy đúng.
Tạo GitHub environment `production`, giới hạn deployment branch `main`.

Environment secrets:

| Secret | Nội dung |
| --- | --- |
| `DEPLOY_HOST` | IP/DNS SSH của máy Windows đích |
| `DEPLOY_USER` | Tài khoản SSH được cấp quyền triển khai/điều khiển service |
| `DEPLOY_SSH_KEY` | Private key riêng cho CD; public key đã cấu hình trên server |
| `DEPLOY_KNOWN_HOSTS` | Dòng OpenSSH host key đã xác minh qua console máy đích |

Không tin ngay kết quả `ssh-keyscan` chưa xác minh. Không gửi secret qua chat hoặc commit.
Với cổng SSH khác 22, known_hosts có dạng `[hostname]:port ssh-ed25519 ...`.

Repository variables:

| Variable | Nội dung |
| --- | --- |
| `DEPLOY_PATH` | `C:\BatTrang` |
| `DEPLOY_PYTHON` | `C:\Python312\python.exe` trên server |
| `DEPLOY_PORT` | Cổng SSH, mặc định `22` |
| `PUBLIC_BASE_URL` | URL HTTPS hiển thị của website |
| `DEPLOY_ENABLED` | `true` khi tất cả mục trên đã sẵn sàng |

Transport SSH dùng đường dẫn tuyệt đối không có dấu cách/ký tự đặc biệt. Các thao tác
deploy local vẫn hỗ trợ đường dẫn có dấu cách. Không cần cấu hình Render/Neon/GHCR hoặc
`RENDER_DEPLOY_HOOK`, `DEPLOY_TARGET` của hướng cũ; chúng không còn được workflow sử dụng.

## Cập nhật và phục hồi

CD bỏ qua commit không còn là head của `main`; server khóa file triển khai để tránh hai
process cập nhật đồng thời và từ chối sequence thấp hơn phiên bản đã triển khai.

Quy trình: xác minh ZIP → giải nén vào release mới → tạo venv/cài offline → dừng service
→ snapshot SQLite → migration → seed nếu DB chưa tồn tại → đổi con trỏ release → start
→ kiểm tra local và public `/health`, bắt buộc JSON `ok` cùng `X-App-Revision` đúng SHA.
Có thời gian ngừng ngắn; không phải zero downtime.

Nếu migration/start/health lỗi, dừng candidate trước khi restore DB, khôi phục con trỏ
và khởi động release cũ. Lần đầu không có release cũ thì giữ service dừng và xóa riêng
DB mới tạo bởi lần triển khai lỗi. Lỗi phục hồi yêu cầu can thiệp thủ công. Job luôn
thất bại khi triển khai lỗi, kể cả rollback thành công.

Snapshot ở `data\backups`, log service ở `logs`. Không tự xóa release/backup. Cần quản lý
dung lượng và có bản sao lưu ngoài máy. Quy trình này dành cho SQLite một instance;
PostgreSQL là lựa chọn riêng, không được áp dụng restore SQLite lên PostgreSQL.

## Phạm vi kiểm chứng

Các test có kiểm tra backup/restore SQLite thật và mô phỏng lỗi service/deployment.
Smoke test chạy ZIP với venv và tiến trình Windows thật. Chưa có Windows server, WinSW
hoặc SSH production được cài/kết nối nên không coi cấu hình này là một lần deploy thật.
Job PostgreSQL cần runner GitHub có PostgreSQL native; local không có thì test được skip.

Nguồn: [GitHub Windows runner image](https://github.com/actions/runner-images/blob/main/images/windows/Windows2025-Readme.md),
[Windows OpenSSH](https://learn.microsoft.com/en-us/windows-server/administration/openssh/openssh_install_firstuse),
[WinSW XML 2.12.0](https://github.com/winsw/winsw/blob/v2.12.0/doc/xmlConfigFile.md).
