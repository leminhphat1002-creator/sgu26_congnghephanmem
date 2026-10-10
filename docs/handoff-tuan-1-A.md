# Handoff Tuần 1: Thành viên A

## Đã làm

- Quy ước repo: `.gitignore`, `.env.example`, `README.md` (Python 3.12), `requirements*.txt`,
  `pyproject.toml` (ruff, pytest).
- `app/core/`: `config.py`, `logging.py`, `exceptions.py` (`AppError`, handler trả
  `{"detail":{"code","message"}}`), `db.py` (engine SQLite bật `foreign_keys`, `get_db` qua
  `Depends`), `health.py` (router `/health`).
- `app/main.py`: `create_app()` chỉ tạo app, đăng ký router; không có logic.
- Khung module `poi`, `content` theo 3 lớp (chỉ docstring nhiệm vụ). `main.py` mới đăng ký
  router của `poi` và `content`; B sẽ thêm router `audio` và `narration` khi dựng khung của mình.
- Alembic (`alembic.ini`, `migrations/env.py`) và migration `0001` tạo bảng `locations`
  (model `Location` ở `app/modules/poi/models.py`).
- `docs/kien-truc-3-lop.md` (chuẩn để B làm theo).
- Test: `tests/test_health.py`, `tests/test_errors.py`, `tests/test_migrations.py`
  (upgrade chạy 2 lần, giá trị mặc định, ràng buộc unique).

## Kết quả kiểm tra (thật)

| Hạng mục | Kết quả |
| --- | --- |
| `pytest` | **Chưa chạy**: môi trường sinh code không cài được phụ thuộc (pypi.org bị chặn) |
| `uvicorn` + `curl /health` | **Chưa chạy**, cùng lý do |
| `alembic upgrade head` | **Chưa chạy**, cùng lý do |
| `ruff check` / `ruff format --check` | **Chưa chạy**; nếu format báo lỗi, chạy `ruff format .` |
| Biên dịch cú pháp Python (`compileall`) | Xem mục "Kiểm tra cú pháp" bên dưới |

Phiên bản trong `requirements*.txt` là phiên bản đã biết là tồn tại nhưng **chưa được cài thử**
trong phiên này. Nếu `pip install` báo lỗi phiên bản, cập nhật số phiên bản gần nhất.

## Lệnh chạy và test

Xem README (mục "Chạy local" và "Test và lint"). Thứ tự khuyến nghị lần đầu:
`pip install -r requirements-dev.txt` → `pytest` → `alembic upgrade head` → `uvicorn ...`.

## Quy ước B cần theo

- Đọc `docs/kien-truc-3-lop.md`: gọi một chiều Presentation → Business → Data Access; DTO ở ranh
  giới; `content`/`audio` không import module khác.
- Mọi lỗi là `AppError(code, message, status_code)`.
- Session DB chỉ lấy qua `Depends(get_db)` và chỉ lớp Data Access dùng.
- Không commit `.env`, `*.db`, MP3.
- Model ORM mới đặt trong `models.py` của module và phải import vào `migrations/env.py`.
- Test đặt trong `tests/`; sang Tuần 4 chuyển về `tests/unit/` và `tests/integration/`.

## Lưu ý cho tuần sau

- `description_source` cho phép `NULL`; `latitude`/`longitude` cho phép `NULL` (bản ghi nhập tay).
- `uq_location_source` không chặn trùng với bản ghi nhập tay vì SQLite coi `NULL` là khác nhau.
- `tests/test_health.py` đặt ở thư mục gốc `tests/` đúng theo prompt; khi tách `tests/unit`
  (Tuần 4/5) cần cập nhật đường dẫn trong CI.
