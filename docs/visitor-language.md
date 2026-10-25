# Ngôn ngữ cho khách tham quan

Giao diện công khai, trang QR, danh sách, popup bản đồ, thông báo và nút thao tác
hỗ trợ tiếng Việt, English, 日本語. Nội dung và giọng đọc dùng ba bản thuyết minh
đã có trong hệ thống; không gửi văn bản đến dịch vụ dịch tự động.

## Luồng sử dụng

1. Lần đầu truy cập, gợi ý một ngôn ngữ được hỗ trợ theo danh sách ngôn ngữ
   trình duyệt. Nếu không có ngôn ngữ phù hợp, dùng English làm gợi ý.
2. Hiện hộp chào hỏi với tên ba ngôn ngữ viết bằng chính ngôn ngữ đó. Khách
   có thể chọn quốc gia/khu vực để nhận gợi ý: Việt Nam → tiếng Việt,
   Nhật Bản → tiếng Nhật, Hoa Kỳ/Anh/Úc → English. Quốc gia là tùy chọn;
   khách ở quốc gia khác có thể bỏ qua và chọn một trong ba ngôn ngữ.
3. Khách có thể chọn ngôn ngữ khác với gợi ý của quốc gia. Chỉ khi nhấn
   nút tiếp tục, lựa chọn mới được lưu và áp dụng cho giao diện/thuyết minh.
4. Lần sau mở lại, dùng lựa chọn đã lưu. Nút **Language / Ngôn ngữ / 言語**
   ở đầu trang mở lại hộp chọn. Bộ chọn Language ở bản đồ cũng đổi cả giao diện.

Đổi ngôn ngữ giữ địa điểm, chế độ GPS và bộ lọc hiện tại; bài đang chọn được
tải bằng ngôn ngữ mới. Âm thanh cũ dừng và bài mới không tự phát. Tìm kiếm nhận
cả tên gốc tiếng Việt và tên đã dịch đang hiển thị. Tên đường trong dữ liệu
địa lý được giữ nguyên để đối chiếu với biển đường thực tế.

## Lưu trữ và phạm vi

Chỉ lưu mã ngôn ngữ và mã quốc gia tùy chọn vào `localStorage`, khóa
`bat-trang-visitor-language-v1`, trên trình duyệt và địa chỉ website hiện tại.
Không lưu vào tài khoản hoặc cơ sở dữ liệu chung, không tra IP, không cần
quyền GPS. Người dùng trình duyệt khác có lựa chọn riêng. Những người dùng
chung một hồ sơ trình duyệt sẽ dùng chung lựa chọn đã lưu; có thể đổi lại
bằng nút Language. Xóa dữ liệu website sẽ làm xuất hiện bước chọn lần đầu.

Nếu trình duyệt chặn lưu trữ, lựa chọn vẫn hoạt động trong lần mở hiện tại
và hộp chọn báo không thể ghi nhớ. Dữ liệu lưu sai hoặc ngôn ngữ không được
hỗ trợ được bỏ qua. Bước gợi ý và xem trước không ghi dữ liệu.

Trang quản lý giữ giao diện tiếng Việt. Các tên/mô tả mặc định của năm điểm
Bát Tràng có bản dịch trong `app/static/app/i18n.js`. Nội dung mới do quản lý
nhập chưa có bản dịch sẽ giữ nguyên, cần bổ sung bản dịch nếu mở rộng catalog.
Nếu thiếu một bài thuyết minh, API giữ cơ chế trả bản thay thế và giao diện
thông báo ngôn ngữ thực tế. Muốn thêm ngôn ngữ thứ tư cần thêm cả giao diện,
bài viết, hỗ trợ API và giọng đọc phù hợp.

## Kiểm tra trên Windows

```powershell
node --test tests/frontend/i18n.test.cjs
python -m pytest tests/test_frontend.py tests/test_local_map.py -q
```

Các kiểm thử JavaScript chạy bằng Node 22 trong CI Windows, không cần npm
package. Bao gồm gợi ý ngôn ngữ, quốc gia và quyền chọn lại, lưu sau xác nhận,
khôi phục khi tải lại, tách lựa chọn giữa trình duyệt, lưu trữ bị chặn/hỏng,
và kiểm tra đủ nhãn dịch cùng tham số của cả hai ngôn ngữ.
