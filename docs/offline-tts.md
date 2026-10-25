# Giọng đọc tại máy chủ Windows

Trang người dùng dùng [Piper 1.8.0](https://github.com/OHF-Voice/piper1-gpl), chạy CPU,
và bộ mã hóa [lameenc](https://pypi.org/project/lameenc/). Không gọi Edge TTS trong luồng nghe
mới. Piper có giấy phép GPL-3.0; nguồn, giấy phép và hướng dẫn Python ở dự án gốc.
Các gói Python được tải từ PyPI; mô hình ONNX/config được tải từ kho chính thức
[rhasspy/piper-voices](https://huggingface.co/rhasspy/piper-voices).

| Ngôn ngữ | Mô hình | Thông tin nguồn/dataset được giữ nguyên |
| --- | --- | --- |
| Việt | vi_VN-vais1000-medium | [VAIS1000, CC BY 4.0](voices/vi_VN-vais1000-medium.md) |
| Anh | en_US-ljspeech-medium | [LJ Speech, public domain](voices/en_US-ljspeech-medium.md) |
| Nhật | ja_JP-hi_fi_captain-medium | [Hi-Fi-Captain, CC BY-NC-SA 4.0](voices/ja_JP-hi_fi_captain-medium.md) |

Giữ attribution/model card khi chia sẻ gói đồ án; giọng Nhật dùng dữ liệu với điều kiện
phi thương mại của CC BY-NC-SA. Bản ZIP chứa các model card cùng mô hình. Manifest trong
`app/modules/audio/offline_voices.json` ghim revision và checksum của từng file.

Sau khi cài `requirements-dev.txt`, chạy trong PowerShell:

```powershell
python -m scripts.setup_offline_tts
python -m scripts.check_offline_tts
python -m scripts.prepare_narration_audio
```

Lệnh kiểm tra dùng cache trống và chặn kết nối socket, vì vậy không thể thành công chỉ nhờ
các MP3 tạo từ Edge TTS trước đó. Không cần ngắt mạng Windows hoặc đổi tường lửa máy thật.
Lệnh tạo trước đọc bài hiện có trong DB, không sửa tài khoản, GPS hoặc nội dung.

`GET .../speech` kiểm tra phiên bản bài viết để tránh phát giọng khác với văn bản đang xem.
Audio mới được gửi từng đoạn qua HTTP; chỉ cache sau khi tạo hoàn tất. Hủy nghe giữa chừng
không lưu file thiếu. Bản cache đã hoàn tất hỗ trợ HTTP Range để tua. Khi chưa có file,
khách cần chờ xử lý đoạn đầu; thời gian phụ thuộc CPU và việc mô hình đã nạp vào RAM hay chưa.
Không có dịch vụ máy chủ nào bảo đảm chạy khi máy chủ tắt hoặc thiếu tài nguyên.
