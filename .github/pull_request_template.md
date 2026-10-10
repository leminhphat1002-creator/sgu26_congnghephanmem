## Mô tả

<!-- Thay đổi gì và vì sao? Liên kết tới tuần/nhiệm vụ trong lộ trình. -->

## Checklist

- [ ] Đúng 3 lớp: router không chứa nghiệp vụ/DB/HTTP ngoài; service không biết FastAPI
      Request/Response; truy cập dữ liệu nằm ở lớp Data Access
- [ ] Đúng quy tắc phụ thuộc giữa module (`content` và `audio` không import module khác)
- [ ] Có test cho thay đổi và đã chạy `pytest` (ghi kết quả thật bên dưới)
- [ ] Đã chạy `ruff check .` và `ruff format --check .`
- [ ] Không commit secret (`.env`, token), DB (`*.db`) hoặc MP3
- [ ] Đã cập nhật tài liệu / handoff nếu đổi API hoặc cấu trúc

## Kết quả kiểm tra

<!-- Dán đầu ra của pytest/ruff. Chưa chạy thì ghi rõ "chưa chạy". -->
