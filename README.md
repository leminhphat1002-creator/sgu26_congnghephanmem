# Thuyết minh tự động đa ngôn ngữ (GPS, Wikimedia, Edge TTS)

Đồ án CNPM, nhóm 2 thành viên, hướng BE Dev: **modular monolith 1 service**, kiến trúc **3 lớp**,
có CI/CD. Người dùng mở app, cho phép GPS, chọn ngôn ngữ; service tìm địa điểm gần, lấy nội
dung từ Wikimedia, tạo MP3 bằng Edge TTS và trả về để tự phát.

> Trạng thái: **Tuần 1** (nền móng repo, core, khung module, Docker). Chưa có nghiệp vụ.

## Phiên bản thống nhất

- **Python 3.12** (Dockerfile, CI và máy dev cùng dùng 3.12).
- Phụ thuộc đã pin trong `requirements.txt` và `requirements-dev.txt`.

## Chạy local

```bash
python3.12 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env                 # chỉnh WIKIMEDIA_USER_AGENT trước Tuần 3
alembic upgrade head                 # tạo data/app.db
uvicorn app.main:app --reload --port 8000
```

Kiểm tra: `curl http://localhost:8000/health` → `{"status":"ok"}`. Tài liệu API: `/docs`.

## Test và lint

```bash
pytest
ruff check . && ruff format --check .
```

## Chạy bằng Docker Compose

```bash
docker compose up --build
curl http://localhost:8000/health
```

SQLite (`/app/data`) và MP3 (`/app/audio_files`) nằm trong named volume, còn sau khi restart.
Không dùng `docker compose down -v` nếu muốn giữ dữ liệu.

## Cấu trúc thư mục

```
app/
  main.py                  # tạo app, đăng ký router
  core/                    # config, logging, exceptions, db, health
  modules/{poi,content,audio,narration}/   # mỗi module có 3 lớp
  static/app/              # client mỏng (Tuần 5)
migrations/                # Alembic
tests/
scripts/
.github/                   # PR template, workflow CI
```

## Quy tắc dữ liệu

Không commit `.env`, file DB (`*.db`), MP3 hay thư mục `data/`, `audio_files/` (đã có trong
`.gitignore`). Secrets lưu trong GitHub Secrets và biến môi trường runtime.

## Giới hạn

Đây là đồ án học tập. Wikimedia có thể thiếu bài, tọa độ hoặc bản ngôn ngữ; `edge-tts` (Tuần 2)
là thư viện cộng đồng dùng dịch vụ online, không phải Azure Speech API chính thức. Bộ đếm rate
limit và khóa trong bộ nhớ (các tuần sau) chỉ đúng với một process.
