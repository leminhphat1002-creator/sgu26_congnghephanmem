# Handoff Tuần 2: Thành viên B – Audio

## Đã làm

- `app/modules/audio/store.py`: triển khai lớp lưu trữ cache MP3, tạo khóa cache bằng SHA-256, kiểm tra file tồn tại, đọc và ghi file. Ghi file an toàn thông qua file tạm và thay thế file đích; kiểm tra đường dẫn để hạn chế truy cập ngoài thư mục cache.
- `app/modules/audio/tts_client.py`: tích hợp `edge-tts` để tổng hợp giọng nói thành MP3; ánh xạ ngôn ngữ `vi`, `en`, `ja` sang voice tương ứng; kiểm tra ngôn ngữ không hỗ trợ, văn bản rỗng và timeout.
- `tests/test_tts_client.py`: có các trường hợp kiểm thử ánh xạ ngôn ngữ, ngôn ngữ không hỗ trợ, văn bản rỗng và timeout.
- `tests/test_audio_store.py`: file kiểm thử cho thành phần lưu trữ cache Audio.
- Commit phần Audio tuần 2: `36babcb feat(audio): implement TTS and MP3 cache`.

## Kết quả kiểm tra

| Hạng mục | Kết quả |
| --- | --- |
| `python -m pytest -v` | Theo báo cáo khi thực hiện: tất cả test đã PASS |
| Test riêng module Audio | Đã chạy theo báo cáo khi thực hiện |
| `python scripts/smoke_audio.py` | Đã chạy theo báo cáo khi thực hiện |
| `git push origin main` | Đã thực hiện; cần đối chiếu GitHub nếu cần xác nhận commit hiện có trên remote |

*Lưu ý: Các kết quả trên được ghi lại theo tiến độ đã trao đổi; chưa có log đầu ra đầy đủ trong tài liệu này để xác minh độc lập.*

## Lưu ý

- `app/modules/audio/service.py` chưa triển khai nghiệp vụ hoàn chỉnh; phần chuẩn hóa văn bản, tính khóa cache, xử lý cache hit/miss và khóa theo cache key thuộc công việc tiếp theo.
- `app/modules/audio/api.py` chưa triển khai đầy đủ các endpoint Audio.
- Giao diện trong `app/static/app/` chưa thuộc phạm vi tuần này; theo lộ trình dự án, phần client mỏng thực hiện ở Tuần 5.
- Tại lần kiểm tra Git trước đó, `alembic.ini` có thay đổi và thư mục `audio_cache/` chưa được theo dõi. Cần kiểm tra lại `git status` trước khi commit tiếp; không tự ý xóa hoặc thêm các mục này.
- Cần đối chiếu `tests/test_audio_store.py` trong repo để chắc chắn các test lưu trữ đã được viết và có nội dung phù hợp.

## Công việc tiếp theo

- Triển khai `app/modules/audio/service.py` theo kiến trúc 3 lớp.
- Chuẩn hóa văn bản đầu vào và tính khóa cache.
- Xử lý cache hit/miss, tránh tổng hợp trùng khi nhiều yêu cầu dùng cùng khóa.
- Chuẩn hóa xử lý lỗi TTS không khả dụng theo quy ước của dự án.
- Bổ sung và chạy test cho Business Service trước khi triển khai API Audio ở giai đoạn sau.