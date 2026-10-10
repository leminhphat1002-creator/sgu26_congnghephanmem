# Kiến trúc 3 lớp trong modular monolith

Một service FastAPI duy nhất (port 8000). Mỗi module (`poi`, `content`, `audio`, `narration`)
tự chia 3 lớp. Đây là chuẩn để cả hai thành viên viết code và review chéo.

## 1. Định nghĩa 3 lớp

| Lớp | File trong module | Nhiệm vụ | Không được làm |
| --- | --- | --- | --- |
| **1. Presentation** | `api.py`, `schemas.py` | Nhận request, validate đầu vào, gọi service, trả response và mã lỗi HTTP | Chứa nghiệp vụ; truy cập CSDL; gọi HTTP ra ngoài; import `sqlalchemy`, `httpx`, `edge_tts` |
| **2. Business** | `service.py` | Quy tắc nghiệp vụ và điều phối: Haversine, chọn điểm kích hoạt, TTL/invalidation cache, chuỗi fallback ngôn ngữ, ngân sách timeout | Biết FastAPI `Request`/`Response`; truy cập SQLite hay mạng trực tiếp |
| **3. Data Access** | `repository.py`, `models.py`, `wikimedia_client.py`, `tts_client.py`, `store.py` | Làm việc với nguồn dữ liệu: SQLite, Wikimedia API, Edge TTS, file MP3 | Chứa quy tắc nghiệp vụ |

Code dùng chung nằm ở `app/core/`: `config.py` (biến môi trường), `logging.py`,
`exceptions.py` (`AppError`), `db.py` (engine, `Base`, `get_db`), `health.py` (router `/health`).

## 2. Quy tắc phụ thuộc

**Trong một module:** gọi một chiều `Presentation → Business → Data Access`, không nhảy cách lớp
(router không gọi thẳng repository).

```
api.py  ──▶  service.py  ──▶  repository.py / *_client.py / store.py
(Lớp 1)       (Lớp 2)                    (Lớp 3)
```

**Giữa các module:**

- `narration` gọi `poi`, `content`, `audio`.
- `poi` gọi `content` (để khám phá bài Wikimedia).
- `content` và `audio` **không import module nào khác**.
- Không có vòng phụ thuộc.

```
narration ──▶ poi ──▶ content
    │
    ├────────────────▶ content
    └────────────────▶ audio
```

Module gọi nhau ở **lớp Business** (service gọi service), không gọi qua HTTP vòng lại
endpoint của chính app.

## 3. Dữ liệu qua ranh giới lớp

- Dùng schema (DTO, Pydantic) khi dữ liệu đi qua ranh giới lớp hoặc module.
- **Không trả thẳng model ORM** (`Location`...) ra ngoài lớp Data Access.
- Truyền phụ thuộc (session, client, service) bằng `Depends` hoặc constructor để test thay Data
  Access bằng mock hoặc SQLite tạm.

## 4. Quy ước đặt tên

| Thứ | Quy ước | Ví dụ |
| --- | --- | --- |
| Module | số ít, chữ thường | `poi`, `content` |
| Router | biến `router` trong `api.py` | `router = APIRouter(tags=["poi"])` |
| Service | hàm hoặc lớp `XxxService` trong `service.py` | `find_nearby`, `choose_activation` |
| Repository | `XxxRepository` hoặc hàm `get_/list_/create_/update_/delete_` | `LocationRepository` |
| Schema | hậu tố mô tả vai trò | `LocationCreate`, `LocationOut`, `CandidateOut` |
| Model ORM | danh từ số ít (bảng số nhiều) | `Location` ↔ `locations` |
| Lỗi nghiệp vụ | `AppError(code, message, status_code)`, `code` là `snake_case` ổn định | `tts_unavailable`, `rate_limited` |
| File test | `tests/unit/test_<module>_<lớp>.py` | `test_poi_service.py` |

Mọi lỗi trả dạng `{"detail": {"code": "...", "message": "..."}}`.

## 5. Kiểm tra tuân thủ

- Tuần 4: `tests/unit/test_layers.py` (router không import `sqlalchemy`/`httpx`/`edge_tts`; service
  không import `fastapi` Request/Response; `content` và `audio` không import module khác).
- Checklist trong `.github/pull_request_template.md` và review chéo mỗi PR.

## 6. Mô hình dữ liệu (Tuần 1)

Bảng `locations` (model `Location` ở `app/modules/poi/models.py`, migration `0001`):

| Cột | Ghi chú |
| --- | --- |
| `id` | khóa nội bộ tự tăng |
| `name`, `description_source` | tên và nội dung gốc |
| `latitude`, `longitude` | cho phép `NULL` (bản ghi nhập tay); không gán 0,0 |
| `radius` | mét, mặc định 80 (cấu hình demo) |
| `source`, `source_lang`, `source_title`, `source_page_id`, `source_url` | nguồn Wikimedia |
| `last_synced_at`, `is_ready` | đồng bộ và trạng thái |

Ràng buộc `uq_location_source` trên (`source`, `source_lang`, `source_page_id`). SQLite coi `NULL`
là khác nhau nên bản ghi nhập tay không bị chặn bởi ràng buộc này.
