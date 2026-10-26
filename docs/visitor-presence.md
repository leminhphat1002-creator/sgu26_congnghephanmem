# Khách đang hoạt động

Dashboard có ô **KHÁCH ĐANG HOẠT ĐỘNG**, ước lượng số trình duyệt khách có tín hiệu
trong 120 giây gần nhất. Chỉ số này độc lập với số yêu cầu lấy thuyết minh.

## Luồng hoạt động

1. Trang `/` nạp `app/static/app/presence.js`.
2. Khi trang đang hiển thị, script gửi `POST /api/presence/heartbeat` ngay và mỗi
   30 giây. Tải lại trang, trở lại tab hoặc có mạng trở lại sẽ thử gửi tiếp.
3. Server cấp cookie phiên ẩn danh `bat_trang_visitor`: HttpOnly, SameSite=Lax,
   Secure trên HTTPS, giới hạn đường dẫn `/api/presence`. Không cần đăng nhập.
4. Các tab cùng trình duyệt/origin dùng chung cookie và cập nhật cùng một mục.
5. Server dùng đồng hồ monotonic và khóa đồng bộ để cập nhật bộ nhớ an toàn giữa
   các thread. Mục không có tín hiệu trong 120 giây bị loại khi đọc/cập nhật.
6. Dashboard lấy số ban đầu qua `/api/admin/dashboard`, sau đó gọi
   `GET /api/admin/presence` mỗi 15 giây khi tab quản lý hiển thị. Hai API thống kê
   đều cần phiên quản trị hợp lệ. Lỗi mạng hiển thị dấu gạch, không giả làm số 0.

Trang quản lý và trang QR không gửi heartbeat. Nếu người quản lý mở thêm trang
khách thì trình duyệt đó được tính như một trình duyệt khách bình thường.
Không gửi sự kiện rời trang để trừ ngay vì có thể còn tab khác đang mở; dùng thời
gian hết hạn tránh trừ nhầm. Tab nền không gửi tín hiệu; trở lại tab sẽ gửi tiếp.

## Dữ liệu và giới hạn

- Lưu tạm mã ngẫu nhiên và thời điểm nhận tín hiệu trong RAM; không lưu vào SQLite,
  không cần migration, không ghi IP, GPS, tên, quốc gia hoặc lịch sử duyệt trang.
- Cookie dùng cho presence không cấp quyền quản lý. Cookie bị chặn, mạng yếu,
  chế độ tiết kiệm pin hoặc việc trình duyệt trì hoãn timer có thể làm số không chính xác.
- Không phải số người duy nhất: hai thiết bị/trình duyệt hoặc cửa sổ riêng tư có
  thể tính riêng; nhiều người dùng chung trình duyệt có thể được gộp.
- Đây không phải xác minh con người; client tự động có thể gửi tín hiệu.
- Chạy với một process Uvicorn như launcher hiện tại. Restart đặt số về 0, khách
  còn mở trang sẽ xuất hiện lại ở nhịp gửi tiếp theo. Nhiều worker/máy chủ cần kho
  presence dùng chung trước khi mở rộng triển khai.
- Tối đa 10.000 mục còn hoạt động trong RAM; khi đầy, trình duyệt mới nhận 429 và
  thử lại ở nhịp tiếp theo. Trình duyệt đã có mục vẫn cập nhật được.
- Origin khác bị từ chối khi gửi header Origin. Tín hiệu công khai không ghi DB.
- Đổi link tunnel tạo origin/cookie mới. Dùng trang khách và admin trên cùng URL.

## Kiểm tra thủ công

1. Khởi động lại app để nạp code Python mới; đăng nhập `/admin`.
2. Mở trang khách trong tab khác, quay lại dashboard: số tăng ở nhịp cập nhật tiếp.
3. Mở thêm tab khách cùng trình duyệt: vẫn một lượt khi dùng cùng cookie.
4. Mở trang khách trên điện thoại hoặc trình duyệt khác: tăng thêm một lượt.
5. Đóng hoặc đưa toàn bộ tab khách xuống nền; sau hơn 2 phút và nhịp cập nhật tiếp,
   số giảm. Tab đang hiển thị tiếp tục giữ lượt của trình duyệt đó.

Backend: `tests/test_visitor_presence.py` và các ca presence trong `tests/test_admin.py`.
Frontend: `tests/frontend/presence.test.cjs` kiểm tra nhịp gửi, tab nền, lỗi mạng và
ngăn gửi chồng nhau. Hết hạn backend dùng đồng hồ giả để kiểm tra chính xác mốc 120 giây.
`tests/frontend/admin-presence.test.cjs` kiểm tra nhịp cập nhật dashboard, tab nền,
lỗi mạng, phục hồi và dừng cập nhật khi phiên quản lý hết hạn.
