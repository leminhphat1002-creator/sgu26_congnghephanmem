# Handoff Tuần 2: Thành viên A

## Đã làm

- `app/modules/poi/repository.py`: triển khai lớp Data Access cho `Location`, gồm tạo, lấy theo ID, liệt kê, cập nhật và xóa địa điểm; truy vấn các địa điểm có tọa độ GPS trong bounding box.
- `app/modules/poi/service.py`: triển khai công thức Haversine để tính khoảng cách giữa hai tọa độ theo mét; kiểm tra giới hạn vĩ độ, kinh độ; tìm địa điểm gần bằng cách lọc bounding box trước rồi tính khoảng cách thực tế.
- Quy ước GPS: bán kính kích hoạt mặc định **80 mét**; phạm vi tìm địa điểm mặc định **500 mét**. Kết quả tìm kiếm được sắp xếp từ gần đến xa.
- `app/modules/poi/schemas.py`: xây dựng DTO bằng Pydantic v2:
  - `LocationCreate`: dữ liệu tạo địa điểm.
  - `LocationUpdate`: dữ liệu cập nhật địa điểm.
  - `LocationRead`: dữ liệu trả về từ model ORM.
- `tests/test_poi_service.py`: bổ sung kiểm thử cho Haversine, tọa độ không hợp lệ, bán kính kích hoạt, CRUD và tìm địa điểm gần. Sử dụng SQLite tạm thời với `StaticPool` cho các test thao tác cơ sở dữ liệu.
- `docs/handoff-tuan-2-A.md`: tài liệu bàn giao phần POI/GPS của thành viên A.

## Kết quả kiểm tra (thật)

| Hạng mục | Kết quả |
| --- | --- |
| `pytest -v tests/test_poi_service.py` | **Đã chạy: 16 passed** tại thời điểm kiểm tra |
| `pytest -v` | **Đã chạy: 20 passed** tại thời điểm kiểm tra |
| `python -m py_compile` cho `repository.py`, `service.py` | Đã chạy, không báo lỗi cú pháp |
| `python -m py_compile app/modules/poi/schemas.py` | Đã được hướng dẫn chạy; cần xác nhận lại nếu muốn ghi nhận chính thức |
| `git diff --check` | Đã chạy trong terminal; cần kiểm tra lại kết quả sau khi tạo tài liệu bàn giao |
| `ruff check` / `ruff format --check` | Chưa xác nhận đã chạy |
| Kiểm thử API POI | Chưa thực hiện; API/router thuộc giai đoạn sau |

Kết quả test nêu trên là kết quả người thực hiện đã báo tại thời điểm chạy. Cần chạy lại `pytest -v` sau khi hoàn tất các thay đổi cuối cùng để xác nhận trạng thái hiện tại.

## Quy ước và cách sử dụng

- Tiếp tục tuân thủ kiến trúc 3 lớp được mô tả trong `docs/kien-truc-3-lop.md`.
- `repository.py` chịu trách nhiệm truy vấn và thao tác dữ liệu `Location`.
- `service.py` chịu trách nhiệm xử lý nghiệp vụ khoảng cách và tìm địa điểm gần.
- `schemas.py` định nghĩa DTO và kiểm tra dữ liệu tại ranh giới xử lý.
- Không triển khai API/router POI trong phần việc tuần 2; để dành cho giai đoạn API theo kế hoạch.
- Tọa độ `latitude` và `longitude` có thể là `NULL`, vì vậy địa điểm không có GPS không được đưa vào kết quả tìm kiếm gần.
- Bán kính kích hoạt và phạm vi tìm kiếm là hai giá trị khác nhau: mặc định lần lượt là 80 m và 500 m.

## Lưu ý kỹ thuật

- Công thức Haversine sử dụng bán kính Trái Đất `6.371.000` mét.
- Tìm kiếm gần sử dụng bounding box để lọc ứng viên trước, sau đó tính khoảng cách Haversine để loại các địa điểm nằm ngoài bán kính thực tế.
- Các test database sử dụng SQLite tạm thời; không cần dùng dữ liệu địa điểm thật.
- Cần kiểm tra lại quy tắc dữ liệu đầu vào và các trường của model khi tích hợp với API ở tuần sau.
- Chưa xác nhận việc kiểm thử các trường hợp biên đặc biệt như vùng gần hai cực, đường đổi ngày quốc tế hoặc trường hợp tọa độ chỉ có một trong hai giá trị bị thiếu.

## Các file thuộc phần việc tuần 2

- `app/modules/poi/repository.py