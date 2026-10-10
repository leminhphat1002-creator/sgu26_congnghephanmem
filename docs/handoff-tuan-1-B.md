# Handoff Tuần 1: Thành viên B

## Đã làm

- Khung module `audio` (`api.py`, `schemas.py`, `service.py`, `store.py`, `tts_client.py`) và
  `narration` (`api.py`, `schemas.py`, `service.py`, điều phối, thay vai trò Gateway). Chỉ có
  docstring, chưa gọi dịch vụ ngoài. Router rỗng đã đăng ký trong `app/main.py`.
- `app/static/app/` (rỗng, dành cho client mỏng Tuần 5) và `scripts/` (rỗng).
- `Dockerfile`: `python:3.12-slim`, user không phải root (uid 10001), cài `requirements.txt`,
  bind `0.0.0.0:8000`, `HEALTHCHECK` gọi `/health`, chạy `alembic upgrade head` rồi `uvicorn`.
- `.dockerignore`: loại `.env`, `*.db`, `data/`, `audio_files/`, `.git`, venv. Không `COPY` DB hay MP3.
- `docker-compose.yml`: 1 service `app`, named volume `app_data` (SQLite) và `app_audio`
  (MP3), `env_file` lấy từ `.env.example`, healthcheck.
- `docs/git-workflow.md`, `.github/pull_request_template.md` (checklist 3 lớp, test, secret).
- Bổ sung `docs/kien-truc-3-lop.md`: sơ đồ module, hướng phụ thuộc, lý do chọn modular monolith.
- Ngoài phạm vi prompt Tuần 1: thêm sớm `.github/workflows/ci.yml` (job `lint`, `test-backend`,
  `build-docker`) theo yêu cầu "kiểu CI/CD" của nhóm. A sẽ hoàn thiện ở Tuần 5 (coverage, cache,
  integration test, branch protection).

## Kết quả kiểm tra (thật)

| Hạng mục | Kết quả |
| --- | --- |
| `docker compose up --build` | **Chưa chạy**: máy sinh code không có Docker daemon đang chạy |
| `curl localhost:8000/health` từ máy host | **Chưa chạy** |
| Workflow CI trên GitHub Actions | **Chưa chạy**: chưa push được lên GitHub trong phiên tạo code |
| Cú pháp YAML của `ci.yml`, `docker-compose.yml` | Đã parse bằng PyYAML: hợp lệ (chưa phải chạy thật) |

Chạy khi có Docker:

```bash
docker compose up --build
curl http://localhost:8000/health        # kỳ vọng {"status":"ok"}
docker compose ps                        # kỳ vọng service ở trạng thái healthy
docker compose down                      # giữ volume; KHÔNG dùng -v
```

## Lưu ý

- Image chạy `alembic upgrade head` mỗi lần khởi động; chạy lặp an toàn. Tuần 6 `deploy.sh`
  sẽ sao lưu DB trước khi migrate.
- `env_file: .env.example` chỉ để chạy demo dev. Môi trường thật dùng env runtime ngoài repo.
- `.dockerignore` loại `tests/` và `docs/` khỏi image; job CI chạy test trên runner, không trong image.
- Phiên bản phụ thuộc trong `requirements.txt` chưa được cài thử trong phiên tạo code; nếu
  `docker build` lỗi ở bước `pip install`, cập nhật số phiên bản.
