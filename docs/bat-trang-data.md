# Hồ sơ dữ liệu Bát Tràng

Đối chiếu trực tuyến ngày **25/10/2026**. Năm địa điểm dưới đây có tên và nguồn
tham khảo cụ thể. Tọa độ dùng hệ WGS84, được làm tròn đến sáu chữ số thập phân
để lưu nhất quán; số chữ số không phải cam kết độ chính xác đo đạc. **Chưa có
điểm nào được khảo sát thực địa hoặc xác nhận đúng cổng vào.**

## Catalog hiện tại

| Điểm | Vĩ độ | Kinh độ | Căn cứ vị trí |
| --- | --- | --- | --- |
| Chợ gốm Bát Tràng | 20.974974 | 105.912077 | Ghim Leaflet công bố trên [Cổng du lịch Gia Lâm](https://visitgialam.com/vi/place/details/cho-gom-bat-trang-12) |
| Đình làng Bát Tràng | 20.976401 | 105.909711 | Vị trí máy ảnh chụp tại đình trong [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Bat_Trang_communal_house_(2018)_01.jpg); chỉ dùng làm điểm tham khảo gần đình |
| Lò bầu cổ Bát Tràng | 20.976499 | 105.911759 | Ghim Leaflet công bố trên [Cổng du lịch Gia Lâm](https://visitgialam.com/vi/place/details/lo-bau-co-15) |
| Bảo tàng Gốm Bát Tràng | 20.973081 | 105.916266 | POI bản đồ mở OpenFreeMap/OpenStreetMap, đối chiếu [địa chỉ và bản đồ của bảo tàng](https://www.ceramuseum.com/lien-he.html) |
| Chùa Kim Trúc (Bát Tràng) | 20.974306 | 105.910936 | Ghim Leaflet công bố trên [Cổng du lịch Gia Lâm](https://visitgialam.com/vi/place/details/chua-kim-truc-10) |

Hai điểm chủ đề cũ được thay bằng địa điểm cụ thể: “Không gian trưng bày gốm
Bát Tràng” → Bảo tàng Gốm Bát Tràng; “Không gian trải nghiệm làm gốm” → chùa
Kim Trúc. Đây là sửa catalog đồ án, không phải xác nhận hai điểm chủ đề trước
đó từng là những cơ sở thực tế. Hoạt động trải nghiệm vẫn được nhắc trong
bài về chợ, lò gốm và bảo tàng, không đặt một xưởng tưởng tượng trên bản đồ.

## Bằng chứng và các nguồn không chọn

- Chợ: mã HTML của trang công bố
  `CreateMapMarkerByLeaflet('map12', …, 20.9749741392671, 105.912077351636, 14)`.
- Lò bầu: `map15`, `20.9764988423084, 105.91175936906`.
- Chùa Kim Trúc: `map10`, `20.9743057, 105.9109363`.
- Đình: ảnh của **Donald Trung**, chụp ngày 01/03/2018, công bố vị trí máy ảnh
  `20.976401; 105.909711`. Không suy diễn vị trí máy ảnh thành tọa độ cổng.
  Ảnh không được tải hoặc đưa vào ứng dụng. Trang nguồn ghi giấy phép
  [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
- Bảo tàng: lớp POI của vector tile OpenFreeMap, feature `98468982171`, tên
  “Trung tâm Tinh hoa làng nghề Việt”, có tọa độ giải mã
  `20.9730810, 105.9162658`. Tile gốc, phương pháp và ghi nguồn nằm trong
  `coordinate_reference` của tệp nội dung. Dữ liệu địa lý từ OpenStreetMap
  theo [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/), qua OpenMapTiles/OpenFreeMap.
  Bản đồ chính thức của bảo tàng có tâm khung nhìn gần đó
  (`20.972973, 105.916164`), dùng để đối chiếu vùng, không thay tọa độ POI.
- **Không dùng** ghim `21.0224596, 105.8795005` trên
  [trang trung tâm của Cổng du lịch Gia Lâm](https://visitgialam.com/vi/place/details/trung-tam-tinh-hoa-lang-nghe-viet-47):
  vị trí này nằm xa Bát Tràng và mâu thuẫn với bản đồ do bảo tàng công bố.
- Không lấy các giá trị tâm khung nhìn trong iframe Google Maps làm tọa độ
  ghim. Không dựa vào bài tổng hợp đưa tọa độ ngoài vùng Bát Tràng.

## Nội dung và ghi nguồn

Tệp `scripts/content/bat_trang_narrations.json` chứa tên, mô tả, tọa độ, hồ sơ
nguồn, lịch sử mẫu và 15 bài bằng tiếng Việt/Anh/Nhật. Chợ, đình, lò bầu giữ
bài hiện có; hai điểm thay thế có sáu bài mới. Nguồn bổ sung:

- [CSDL du lịch Việt Nam — Làng gốm Bát Tràng](https://csdl.vietnamtourism.gov.vn/dest/?item=198).
- [TTXVN — Nghi thức rước nước](https://vietnam.vnanet.vn/vietnamese/long-form/doc-dao-nghi-thuc-ruoc-nuoc-trong-le-hoi-lang-bat-trang-395142.html).
- [Bảo tàng — Trưng bày thường xuyên](https://www.ceramuseum.com/trung-bay/trung-bay-thuong-xuyen.html).
- [Bảo tàng — Trải nghiệm](https://www.ceramuseum.com/dich-vu/trai-nghiem.html).
- [UBND xã Bát Tràng — Chùa Bát Tràng](https://battrang.hanoi.gov.vn/di-tich-lich-su-va-van-hoa/chua-bat-trang-2757250704153629561.htm).

Giao diện có mô tả nguồn vị trí của từng điểm và liên kết **Nguồn tham khảo**
ở bài đang chọn. Bản dịch giao diện có đủ tên/mô tả mới. Không khẳng định giá
vé hay giờ hoạt động hiện tại trong bài thuyết minh; khách cần xem kênh của
đơn vị tổ chức trước khi đi.

## Cập nhật DB hiện có trên Windows

```powershell
python -m scripts.seed_bat_trang
python -m scripts.prepare_narration_audio
```

Lệnh đầu tự sao lưu SQLite vào `data/backups/before-catalog-*.db` trước khi
ghi, giữ ID để liên kết nội dung và quản trị không bị đứt. Chỉ thay cặp tọa
độ khớp đúng mẫu cũ; không đoán rằng tọa độ người quản lý sửa là sai. Tương
tự, chỉ nâng cấp bài có dấu vân tay khớp bản đã phát hành; bài biên tập riêng
được giữ lại. Khóa catalog ổn định lưu vào `source_title`; giá trị nội bộ
`source=bat_trang_demo` giữ để nhận diện các bản ghi đã phát hành trước đây,
không có nghĩa các vị trí mới là điểm giả lập.

Nếu điểm trải nghiệm cũ có bài, tọa độ hoặc mô tả đã sửa riêng, script dừng
để tránh đổi nhầm thành chùa. CLI đóng giao dịch và hoàn tác các sửa chưa
commit khi có lỗi. Lệnh chạy lại không tạo trùng hoặc ghi đè bài đã biên tập.
Không thay đổi tài khoản hay phiên đăng nhập quản trị. MP3 cũ được giữ;
bài mới dùng khóa cache theo nội dung và giọng đọc mới, tránh phát nhầm bài.

Lệnh thứ hai tạo sẵn các bài chưa có âm thanh bằng Piper cục bộ. DB, bản
sao lưu, MP3 và mô hình giọng đọc không đưa vào Git; nội dung và hồ sơ nguồn
được commit cùng mã để các máy khác seed ra cùng catalog.
