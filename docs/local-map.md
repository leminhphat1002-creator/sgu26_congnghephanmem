# Nền bản đồ Bát Tràng

Giao diện dùng Leaflet có sẵn trong dự án và tập tin
`app/static/app/bat-trang-basemap.geojson` (khoảng 747 KiB). Nền bản đồ được
phục vụ từ chính website, không cần API key, dịch vụ ảnh nền hay Internet trên
server để hiển thị. Người dùng vẫn cần kết nối tới server đang chạy website.

Phạm vi: kinh độ 105.900–105.930, vĩ độ 20.965–20.995, quanh Bát Tràng.
Thu phóng và kéo được giới hạn trong vùng dữ liệu này. Đây là bản trích xuất
địa lý, không phải bản đồ chỉ đường. Tọa độ điểm tham quan đã được đối chiếu từ
nguồn trực tuyến, vẫn cần khảo sát lối vào tại thực địa. Xem [hồ sơ dữ liệu](bat-trang-data.md).

## Nguồn và giấy phép

- Dữ liệu OpenStreetMap qua [OpenFreeMap](https://openfreemap.org/quick_start/),
  theo lược đồ [OpenMapTiles](https://openmaptiles.org/).
- Tập dữ liệu được phân phối theo [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/).
  Ghi nguồn hiển thị ngay trên bản đồ và có liên kết tải GeoJSON bên dưới.
- URL của bốn tile gốc, ngày trích xuất, phạm vi và giấy phép nằm trong
  `metadata` của GeoJSON. Không tải ảnh raster từ máy chủ OpenStreetMap để lưu offline.
- Chính sách OpenFreeMap cho phép tải offline tối đa 3.000 tile hoặc 50 MB,
  không quá bốn yêu cầu đồng thời và dùng User-Agent riêng. Script này chỉ
  lấy bốn vector tile ở mức zoom 14, tuần tự.

## Cập nhật dữ liệu trên Windows

Không cần chạy bước này để khởi động website hoặc build release: dữ liệu đã
nằm trong thư mục `app`, được đóng gói cùng ứng dụng. Công cụ trích xuất có
phụ thuộc riêng, không thêm vào môi trường chạy server:

```powershell
python -m venv .venv\map-export
.venv\map-export\Scripts\python.exe -m pip install mapbox-vector-tile==2.2.0
.venv\map-export\Scripts\python.exe -m scripts.export_bat_trang_map
```

Script lấy TileJSON hiện tại từ OpenFreeMap, giữ các lớp đường, tên đường,
nhà, mặt nước và sử dụng đất, chuyển tọa độ Web Mercator sang WGS84 rồi cắt
đúng phạm vi. Kiểm tra bản đồ và thay phiên bản URL `map.js`/CSS nếu sửa cách
hiển thị. Nếu mở rộng phạm vi quá bốn tile, script dừng để tránh tải ngoài dự kiến.

## Sự cố đã xác minh trên máy phát triển

Ngày 25/10/2026, DNS cho `tile.openstreetmap.org` trả về địa chỉ loopback
`127.0.0.1` và `::1`; tải tile bị từ chối kết nối. Vì vậy nền raster cũ trống
trong khi các điểm vẫn hiển thị. Chưa xác định phần mềm/cấu hình nào tạo ra
kết quả DNS này. Thay đổi hiện tại không sửa DNS hoặc tắt xác minh TLS;
giao diện dùng tập dữ liệu địa lý cục bộ ở trên.
