# Hồ sơ đồ án Bát Tràng Audio Guide

Bộ hồ sơ ngày 26/10/2026, đối chiếu mã nguồn commit 2ef18dec8d7658c5a9a11ca0d0d59ace4befbb91.
Giữ nguyên PRD gốc trong Downloads; không thay thế hoặc sửa tệp gốc đó.

Từ bản cập nhật dashboard, bộ đếm ghi lượt yêu cầu phát vào `activity_events`.
Migration `0006_narration_play` thêm `play_id` để một lần bấm Play chỉ được ghi
một lần khi gửi lại yêu cầu. Dashboard cũng hiển thị các phiên khách đang hoạt động
và vị trí gần đúng nếu khách chọn chia sẻ. Dữ liệu phiên và vị trí chỉ lưu tạm trong
RAM. Xem [cách đếm lượt phát](../../README.md) và [luồng phiên khách](../visitor-presence.md)
khi đối chiếu bản triển khai mới với bộ hồ sơ ngày 26/10.

| Tệp | Dùng để làm gì |
| --- | --- |
| [01 Đánh giá PRD](01_Danh_gia_PRD.docx) | Đọc trước để biết phần hợp lý và các chỗ cần sửa trong PRD 1.0 |
| [02 PRD hiệu chỉnh](02_PRD_hieu_chinh.docx) | Bản 1.1 đối chiếu theo commit của bộ hồ sơ ngày 26/10 |
| [03 Phân tích và thiết kế](03_Phan_tich_va_thiet_ke.docx) | Use Case, kiến trúc, ERD, trình tự, dữ liệu, API và truy vết |
| [04 Kiểm thử](04_Ke_hoach_va_bien_ban_kiem_thu.docx) | Kết quả tự động đã chạy và 38 ca nghiệm thu cần ghi nhận |
| [05 Vận hành và demo](05_Huong_dan_va_kich_ban_demo.docx) | Chạy lại Windows, lấy link QR, sao lưu và kịch bản bảy phút |
| [06 Lược đồ quan hệ dữ liệu](06_Luoc_do_quan_he_du_lieu.docx) | Lược đồ đối chiếu commit `8ef3f27`, trước migration `0006_narration_play` |
| [07 Luồng nghiệp vụ](07_Luong_nghiep_vu.docx) | Luồng đối chiếu commit `8ef3f27`, trước cập nhật bộ đếm Play và chia sẻ vị trí |

Các sơ đồ PNG và nguồn PlantUML nằm trong thư mục so-do. Kết quả tự động đã lược bỏ
thông tin nhạy cảm nằm trong minh-chung/ket-qua-tu-dong.json. Có thể dùng tệp
mau-bien-ban-kiem-thu.csv để ghi các lần kiểm tra thủ công.

Trước khi nộp, điền tên nhóm và giảng viên, thực hiện các ca thủ công phù hợp thiết bị,
đính kèm ảnh hoặc video, và kiểm tra Actions theo commit được nộp. Các ca chưa thực hiện
vẫn phải giữ trạng thái đó. Chỉ tiêu p95 là mục tiêu đề xuất, không phải số đã đo.
Chưa xác nhận triển khai Windows production hoặc website độc lập chạy khi tắt máy.

File Word là bản chỉnh sửa được; PDF và ảnh render chỉ dùng kiểm tra bố cục tại máy lập
hồ sơ, không phải bản báo cáo khác để nộp. Sau khi sửa Word, cần xem lại phân trang và bảng.
