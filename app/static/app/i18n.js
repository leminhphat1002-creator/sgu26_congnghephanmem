"use strict";

// Source strings stay readable in Vietnamese; each entry supplies English and Japanese.
window.BatTrangI18n = (() => {
    const messages = {
        "Khám phá làng gốm Bát Tràng": ["Explore Bát Tràng pottery village", "バッチャン陶芸村を巡る"],
        "Khám phá từ xa hoặc bật GPS khi đến làng gốm, chọn nơi muốn khám phá và nghe thuyết minh bằng ngôn ngữ yêu thích.": ["Explore from anywhere, or use GPS when visiting the village. Choose a place and listen in your preferred language.", "どこからでも村を探索できます。現地ではGPSも利用できます。場所を選び、お好きな言語でガイドをお楽しみください。"],
        "Liên kết website": ["Website links", "サイトリンク"],
        "Mã QR truy cập": ["Visit by QR code", "QRコードでアクセス"],
        "Đăng nhập quản lý": ["Manager sign in", "管理者ログイン"],
        "Vị trí, GPS và chế độ tham quan": ["Location, GPS and visit mode", "位置情報・GPS・見学モード"],
        "Khám phá theo cách của bạn": ["Explore your way", "お好きな方法で探索"],
        "Không cần ở Bát Tràng để đọc và nghe thuyết minh.": ["You can read and listen even when you are away from Bát Tràng.", "バッチャンにいなくても、ガイドを読んだり聞いたりできます。"],
        "Khám phá từ xa": ["Explore remotely", "リモートで探索"],
        "Trải nghiệm vị trí mẫu tại Bát Tràng": ["Try a sample location in Bát Tràng", "バッチャンのサンプル位置を試す"],
        "Khám phá từ xa — không sử dụng GPS.": ["Remote exploration — GPS is not used.", "リモート探索 — GPSは使用しません。"],
        "Khám phá từ xa — không sử dụng GPS": ["Remote exploration — GPS is not used", "リモート探索 — GPSは使用しません"],
        "Bài thuyết minh đã được biên soạn từ nguồn tham khảo. Tọa độ vẫn là minh họa; cần xác minh trước khi tham quan thực tế.": ["Narrations are compiled from reference sources. Coordinates are illustrative and must be verified before an actual visit.", "ガイドは参考資料に基づいて作成されています。座標は例示用です。実際に訪問する前にご確認ください。"],
        "Vị trí tìm kiếm": ["Search location", "検索位置"],
        "Vĩ độ": ["Latitude", "緯度"], "Kinh độ": ["Longitude", "経度"],
        "Lấy vị trí hiện tại": ["Use my location", "現在地を取得"],
        "Tìm địa điểm xung quanh": ["Find nearby places", "近くの場所を検索"],
        "Theo dõi GPS tự động": ["Automatic GPS updates", "GPSの自動更新"],
        "Tự cập nhật danh sách khi bạn di chuyển. Không tự phát âm thanh.": ["Update the list as you move. Audio will not play automatically.", "移動に合わせてリストを更新します。音声は自動再生されません。"],
        "Bật theo dõi GPS": ["Enable GPS tracking", "GPS追跡を有効にする"],
        "Tắt theo dõi GPS": ["Disable GPS tracking", "GPS追跡を停止"],
        "GPS tự động đang tắt.": ["Automatic GPS updates are off.", "GPSの自動更新はオフです。"],
        "GPS tự động đã tắt.": ["GPS tracking has been stopped.", "GPS追跡を停止しました。"],
        "Địa điểm Bát Tràng": ["Places in Bát Tràng", "バッチャンの見どころ"],
        "Địa điểm xung quanh": ["Nearby places", "近くの場所"],
        "500 mét": ["500 metres", "500メートル"],
        "Chọn một địa điểm để đọc và nghe thuyết minh.": ["Choose a place to read and listen to its guide.", "場所を選ぶとガイドを読んだり聞いたりできます。"],
        "Nhấn \"Tìm địa điểm xung quanh\" để bắt đầu.": ["Select “Find nearby places” to begin.", "「近くの場所を検索」を押して開始します。"],
        "BẢN ĐỒ KHÁM PHÁ": ["EXPLORE THE MAP", "地図で探索"],
        "Chọn điểm dừng ở Bát Tràng": ["Choose a stop in Bát Tràng", "バッチャンの訪問先を選ぶ"],
        "Đang tải địa điểm": ["Loading places", "場所を読み込み中"],
        "Chạm vào một điểm đánh dấu để chọn địa điểm và tải bài thuyết minh. Nhấn Play khi muốn nghe.": ["Select a map marker to open its guide. Press Play when you want to listen.", "地図のマーカーを選んでガイドを開きます。聞きたいときに再生ボタンを押してください。"],
        "Tìm địa điểm": ["Search places", "場所を検索"],
        "Ví dụ: chợ gốm, đình làng…": ["Try: pottery market, communal house…", "例：陶器市場、集会所…"],
        "Xóa từ khóa tìm kiếm": ["Clear search", "検索語を消去"],
        "Ngôn ngữ thuyết minh": ["Language", "言語"],
        "Xem tất cả điểm": ["Show all places", "すべての場所を表示"],
        "Bản đồ các địa điểm Bát Tràng": ["Map of places in Bát Tràng", "バッチャンの見どころマップ"],
        "Đang tải bản đồ và các điểm tham quan…": ["Loading the map and places…", "地図と見どころを読み込み中…"],
        "Đọc và nghe thuyết minh ↓": ["Read and listen to the guide ↓", "ガイドを読む・聞く ↓"],
        "Tọa độ và địa điểm trong đồ án là dữ liệu minh họa, cần xác minh trước khi tham quan thực tế.": ["Places and coordinates in this student project are illustrative. Verify them before visiting.", "この学生プロジェクトの場所・座標は例示用です。訪問前にご確認ください。"],
        "Nền bản đồ Bát Tràng được lưu cùng ứng dụng; có thể kéo và phóng to trong khu vực này mà không cần tải ảnh nền từ Internet.": ["The Bát Tràng map is included with this website. Pan and zoom within this area without downloading external map images.", "バッチャンの地図はサイトに含まれています。この範囲では外部の地図画像を読み込まずに移動・拡大できます。"],
        "Dữ liệu bản đồ (ODbL)": ["Map data (ODbL)", "地図データ（ODbL）"],
        "THUYẾT MINH ĐỊA ĐIỂM": ["PLACE GUIDE", "スポットガイド"],
        "Quay lại bản đồ ↑": ["Back to map ↑", "地図に戻る ↑"],
        "Nội dung thuyết minh": ["About this place", "この場所について"],
        "Thử tải lại thuyết minh": ["Reload guide", "ガイドを再読み込み"],
        "Nghe thuyết minh": ["Listen to the guide", "音声ガイドを聞く"],
        "Nghe bằng giọng thiết bị": ["Use device voice", "端末の音声で聞く"],
        "Dừng đọc": ["Stop reading", "読み上げを停止"],
        "Thử phát lại": ["Retry playback", "再生を再試行"],
        "Đồ án Công nghệ phần mềm — Bát Tràng Audio Guide": ["Software Engineering student project — Bát Tràng Audio Guide", "ソフトウェア工学の学生プロジェクト — Bát Tràng Audio Guide"],
        "Từ vị trí mẫu": ["From the sample location", "サンプル位置から"],
        "Từ vị trí tìm kiếm": ["From the search location", "検索位置から"],
        "Vui lòng nhập đủ tọa độ GPS.": ["Enter both GPS coordinates.", "緯度と経度を入力してください。"],
        "Tọa độ GPS không hợp lệ.": ["The GPS coordinates are invalid.", "GPS座標が正しくありません。"],
        "Địa điểm": ["Place", "場所"], "Không xác định": ["Unknown", "不明"],
        "Ngôn ngữ thuyết minh: {language}": ["Guide language: {language}", "ガイドの言語：{language}"],
        " (thay cho {language})": [" (instead of {language})", "（{language}の代わり）"],
        "Chưa có nội dung.": ["No content is available yet.", "まだ内容がありません。"],
        "Nhấn Play để nghe thuyết minh.": ["Press Play to listen to the guide.", "再生ボタンを押してガイドを聞いてください。"],
        "Giọng đọc tại máy chủ, dùng được khi máy chủ không có Internet.": ["Audio is generated on the server and works without the server having Internet access.", "音声はサーバー上で生成されるため、サーバーがインターネットに接続していなくても利用できます。"],
        "Không có bản {requested}. Đang dùng bản {actual}. Bạn có thể đọc bài bên dưới.": ["A {requested} guide is unavailable. Using {actual} instead. Read it below.", "{requested}のガイドがないため、{actual}を表示します。以下でお読みいただけます。"],
        "Đã tải thuyết minh {language}. Bạn có thể đọc bài ngay bên dưới.": ["The {language} guide is ready. You can read it below.", "{language}のガイドを読み込みました。以下でお読みいただけます。"],
        "Có nội dung nhưng chưa tạo được MP3.": ["The text is ready, but audio is unavailable.", "本文はありますが、音声はまだ利用できません。"],
        "Không tìm thấy nội dung thuyết minh.": ["No guide was found for this place.", "この場所のガイドが見つかりません。"],
        "Tạm dừng đọc": ["Pause reading", "読み上げを一時停止"],
        "Tiếp tục đọc": ["Resume reading", "読み上げを再開"],
        "Thiết bị chưa đọc được bài. Bạn vẫn có thể đọc nội dung hoặc dùng MP3.": ["Device speech is unavailable. You can read the text or use the audio player.", "端末での読み上げを利用できません。本文または音声プレーヤーをご利用ください。"],
        "Đang mở giọng đọc…": ["Loading audio…", "音声を読み込み中…"],
        "Đang đọc thuyết minh.": ["Playing the guide.", "ガイドを再生中です。"],
        "Đã tạm dừng. Nhấn Play để tiếp tục.": ["Paused. Press Play to continue.", "一時停止中です。再生ボタンで続けます。"],
        "Đã đọc xong. Nhấn Play để nghe lại.": ["Finished. Press Play to listen again.", "再生が終わりました。再生ボタンでもう一度聞けます。"],
        "Chưa mở được âm thanh. Bạn có thể thử phát lại hoặc tải lại bài nếu nội dung vừa thay đổi.": ["Audio could not be opened. Retry playback, or reload the guide if its content has changed.", "音声を開けませんでした。再生を再試行するか、内容が更新された場合はガイドを再読み込みしてください。"],
        "Không có điểm phù hợp. Hãy thử từ khóa khác hoặc xóa bộ lọc.": ["No matching places. Try another keyword or clear the search.", "一致する場所がありません。検索語を変えるか、検索を解除してください。"],
        "Chưa có địa điểm trong phạm vi này. Chọn Khám phá từ xa để xem toàn bộ địa điểm.": ["No places in this area. Choose Explore remotely to see all places.", "この範囲に場所がありません。「リモートで探索」ですべての場所を表示できます。"],
        "Gần nhất trong danh sách": ["Nearest in this list", "リスト内で最も近い場所"],
        "Xem bài đang chọn": ["View selected guide", "選択中のガイドを表示"],
        "Thuyết minh": ["Open guide", "ガイドを開く"], "Chưa sẵn sàng": ["Not ready yet", "準備中"],
        "Không thể tải danh sách địa điểm.": ["Could not load places. Please try again.", "場所を読み込めませんでした。もう一度お試しください。"],
        "Đã cập nhật vị trí. Tự làm mới khi bạn di chuyển.": ["Location updated. The list refreshes as you move.", "位置を更新しました。移動に合わせてリストを更新します。"],
        "Đã cập nhật danh sách. Giữ bài đang chọn: {name}.": ["Places updated. Keeping your selected guide: {name}.", "リストを更新しました。選択中のガイド「{name}」を維持します。"],
        "Điểm đang chọn không còn trong kết quả. Hãy chọn một điểm khác.": ["Your selected place is outside the results. Please choose another.", "選択中の場所が結果に含まれていません。別の場所を選んでください。"],
        "Có {count} địa điểm để khám phá từ xa.": ["{count} places to explore remotely.", "{count}か所をリモートで探索できます。"],
        "Đã tìm thấy {count} địa điểm trong 500 mét.": ["Found {count} places within 500 metres.", "500メートル以内に{count}か所見つかりました。"],
        "Bạn đang ở xa các địa điểm đã lưu. Chọn Khám phá từ xa để tiếp tục.": ["You are far from the listed places. Choose Explore remotely to continue.", "登録された場所から離れています。「リモートで探索」を選んで続けてください。"],
        "Chưa cập nhật được danh sách. Hãy kiểm tra kết nối.": ["Could not update places. Check your connection.", "リストを更新できませんでした。接続をご確認ください。"],
        "Đang tải {language}…": ["Loading {language}…", "{language}を読み込み中…"],
        "Đang lấy nội dung…": ["Loading the guide…", "ガイドを読み込み中…"],
        "Đang chuẩn bị thuyết minh: {name}…": ["Preparing the guide: {name}…", "ガイドを準備中：{name}…"],
        "Không thể lấy thuyết minh.": ["Could not load the guide. Please try again.", "ガイドを読み込めませんでした。もう一度お試しください。"],
        "Kết nối quá lâu. Bạn có thể thử tải lại bài.": ["The connection timed out. Please reload the guide.", "接続がタイムアウトしました。ガイドを再読み込みしてください。"],
        "Ngôn ngữ: {language}": ["Language: {language}", "言語：{language}"],
        "Trình duyệt không hỗ trợ GPS.": ["This browser does not support GPS.", "このブラウザーはGPSに対応していません。"],
        "Thiết bị không hỗ trợ GPS.": ["This device does not support GPS.", "この端末はGPSに対応していません。"],
        "Đang lấy GPS hiện tại...": ["Getting your location…", "現在地を取得中…"],
        "Không lấy được GPS. Hãy kiểm tra quyền vị trí và thử lại.": ["Could not get your location. Check location permission and try again.", "位置を取得できませんでした。位置情報の許可を確認して再試行してください。"],
        "GPS chưa đủ chính xác để cập nhật danh sách.": ["GPS is not accurate enough to update the list yet.", "GPSの精度が低いため、まだリストを更新できません。"],
        "Đang cập nhật danh sách địa điểm...": ["Updating places…", "場所を更新中…"],
        "Đang chờ GPS...": ["Waiting for GPS…", "GPSを待機中…"],
        "Đã tắt GPS vì chưa được cấp quyền vị trí.": ["GPS was stopped because location permission was not granted.", "位置情報が許可されていないため、GPSを停止しました。"],
        "Đã đổi ngôn ngữ. Hãy chọn địa điểm muốn nghe.": ["Language changed. Choose a place to listen to its guide.", "言語を変更しました。ガイドを聞きたい場所を選んでください。"],
        "Hiển thị {count}/{total} địa điểm.": ["Showing {count} of {total} places.", "{total}か所中{count}か所を表示中。"],
        "Vị trí mô phỏng tại Bát Tràng — không phải vị trí thiết bị.": ["Sample location in Bát Tràng — not your device location.", "バッチャンのサンプル位置 — 端末の現在地ではありません。"],
        "Sử dụng GPS thực tế của thiết bị.": ["Using your device's actual GPS location.", "端末の実際のGPS位置を使用しています。"],
        "Tìm theo tọa độ nhập thủ công — không phải GPS thiết bị.": ["Searching manually entered coordinates — not device GPS.", "手動入力した座標で検索 — 端末のGPSではありません。"],
        "Chọn trong danh sách": ["Choose from the list", "リストから選択"],
        "Không mở được bản đồ. Bạn vẫn có thể chọn địa điểm trong danh sách bên dưới.": ["The map is unavailable. You can still choose a place from the list.", "地図を開けません。リストから場所を選べます。"],
        "Đang mở nền bản đồ Bát Tràng…": ["Opening the Bát Tràng map…", "バッチャンの地図を開いています…"],
        "Chưa mở được nền bản đồ. Bạn vẫn có thể chọn điểm đánh dấu. ": ["Map background unavailable. You can still select a marker. ", "地図の背景を開けません。マーカーは選択できます。 "],
        "Tải lại nền bản đồ": ["Reload map background", "地図の背景を再読み込み"],
        "Chọn điểm để khám phá từ xa.": ["Select this place to explore remotely.", "この場所を選んでリモートで探索できます。"],
        "Cách vị trí tìm kiếm {distance} m.": ["{distance} m from the search location.", "検索位置から{distance} m。"],
        "Chọn {name}": ["Select {name}", "{name}を選択"],
        "{count} điểm trên bản đồ": ["{count} places on the map", "地図上に{count}か所"],
        " · {count} điểm chưa có tọa độ": [" · {count} places have no coordinates", " · {count}か所は座標が未登録"],
        "Phóng to": ["Zoom in", "拡大"], "Thu nhỏ": ["Zoom out", "縮小"], "Đóng": ["Close", "閉じる"],
        "Chợ gốm Bát Tràng": ["Bát Tràng Pottery Market", "バッチャン陶器市場"],
        "Đình làng Bát Tràng": ["Bát Tràng Communal House", "バッチャンの集会所（ディン）"],
        "Lò bầu cổ Bát Tràng": ["Bát Tràng Traditional Kiln", "バッチャンの伝統的な窯"],
        "Không gian trưng bày gốm Bát Tràng": ["Bát Tràng Pottery Display Space", "バッチャン陶器展示スペース"],
        "Không gian trải nghiệm làm gốm": ["Pottery Experience Space", "陶芸体験スペース"],
        "Khám phá sản phẩm gốm và cách quan sát hình dáng, men, hoa văn. Tọa độ demo chưa khảo sát.": ["Explore pottery shapes, glazes and patterns. Sample coordinates have not been surveyed.", "陶器の形、釉薬、模様を楽しみます。サンプル座標は未調査です。"],
        "Tìm hiểu đình làng và nghi thức rước nước sông Hồng trong hội làng. Tọa độ demo chưa khảo sát.": ["Discover the communal house and the festival's Red River water procession. Sample coordinates have not been surveyed.", "村の集会所と祭りの紅河の水を運ぶ儀式を紹介します。サンプル座標は未調査です。"],
        "Câu chuyện nung gốm, lò truyền thống và sự thay đổi công nghệ. Tọa độ demo chưa khảo sát.": ["Learn about pottery firing, traditional kilns and changing technology. Sample coordinates have not been surveyed.", "焼成、伝統的な窯、技術の変化を紹介します。サンプル座標は未調査です。"],
        "Điểm chủ đề về trưng bày và quan sát gốm; không phải vị trí đã xác minh của Bảo tàng Gốm Bát Tràng.": ["A themed stop about pottery displays, not a verified location of the Bát Tràng Pottery Museum.", "陶器の展示を紹介するテーマスポットです。バッチャン陶器博物館の確認済み所在地ではありません。"],
        "Điểm chủ đề về tạo hình và trang trí gốm; chưa gắn với một cơ sở trải nghiệm cụ thể.": ["A themed stop about shaping and decorating pottery, not a specific verified workshop.", "成形や装飾を紹介するテーマスポットです。特定の体験施設には対応していません。"],
        "Bạn đến từ đâu?": ["Where are you visiting from?", "どちらからお越しですか？"],
        "Quốc gia / khu vực (không bắt buộc)": ["Country / region (optional)", "国・地域（任意）"],
        "Chọn quốc gia để gợi ý ngôn ngữ. Bạn luôn có thể chọn ngôn ngữ khác.": ["Choose a country for a language suggestion. You can always choose a different language.", "国を選ぶと言語をご提案します。別の言語も自由に選べます。"],
        "Quốc gia khác / bỏ qua": ["Another country / skip", "その他の国・スキップ"],
        "Tiếp tục khám phá": ["Start exploring", "探索を始める"],
        "Lựa chọn chỉ lưu trên trình duyệt này và có thể đổi bất cứ lúc nào.": ["Your preference is saved only in this browser. Change it at any time.", "設定はこのブラウザーにのみ保存され、いつでも変更できます。"],
        "Trình duyệt không cho lưu lựa chọn; bạn vẫn dùng được ngôn ngữ này trong lần mở hiện tại.": ["This browser cannot save your preference. Your choice still works for this visit.", "このブラウザーには設定を保存できませんが、今回の閲覧中は選んだ言語をご利用いただけます。"],
        "Quét QR khám phá Bát Tràng": ["Scan a QR code to explore Bát Tràng", "QRコードでバッチャンを探索"],
        "Quét mã. Bắt đầu khám phá.": ["Scan the code. Start exploring.", "コードを読み取って、探索を始めましょう。"],
        "Mở camera điện thoại, quét mã QR và nghe câu chuyện làng gốm.": ["Open your phone camera, scan the QR code and listen to the village's stories.", "スマートフォンのカメラでQRコードを読み取り、陶芸村の物語を聞いてみましょう。"],
        "Mã QR mở trang người dùng Bát Tràng": ["QR code for the Bát Tràng visitor page", "バッチャンの訪問者ページ用QRコード"],
        "Đang kiểm tra đường dẫn…": ["Checking the link…", "リンクを確認中…"],
        "Tải mã QR": ["Download QR code", "QRコードをダウンロード"],
        "Sao chép liên kết": ["Copy link", "リンクをコピー"],
        "In mã QR": ["Print QR code", "QRコードを印刷"],
        "Vào trang khám phá": ["Open the visitor page", "探索ページを開く"],
        "Chưa cấu hình được đường dẫn QR.": ["The QR link is not configured yet.", "QRコードのリンクはまだ設定されていません。"],
        "Mã hiện trỏ về localhost, điện thoại chưa mở được. Cần cấu hình địa chỉ LAN hoặc tên miền.": ["This code points to localhost and cannot be opened on a phone yet. Configure a LAN address or domain.", "このコードはlocalhostを指しているため、スマートフォンでは開けません。LANアドレスかドメインの設定が必要です。"],
        "Điện thoại và máy chủ cần cùng mạng Wi-Fi. Giữ máy chủ đang chạy.": ["Your phone and server must be on the same Wi-Fi network. Keep the server running.", "スマートフォンとサーバーを同じWi-Fiに接続し、サーバーを起動したままにしてください。"],
        "Khách có thể quét mã để mở trang khám phá.": ["Visitors can scan the code to open the visitor page.", "コードを読み取ると探索ページを開けます。"],
        "Đã sao chép liên kết.": ["Link copied.", "リンクをコピーしました。"],
        "Hãy sao chép địa chỉ hiển thị phía trên.": ["Please copy the address shown above.", "上に表示されたアドレスをコピーしてください。"],
        "Nội dung và vị trí đã đối chiếu từ nguồn trực tuyến. Tọa độ chỉ để tham khảo, chưa khảo sát thực địa hoặc xác nhận lối vào.": ["Content and locations have been checked against online sources. Coordinates are references only; entrances have not been surveyed on site.", "内容と位置はオンライン資料と照合しています。座標は参考値です。入口の現地調査は行っていません。"],
        "Vị trí tham khảo trực tuyến, chưa khảo sát thực địa. Hãy đối chiếu biển chỉ dẫn tại điểm đến.": ["These are online reference positions, not field-surveyed locations. Check signs at the destination.", "位置はオンライン資料による参考値です。現地調査済みではありません。訪問先の案内表示をご確認ください。"],
        "Nguồn tham khảo ↗": ["Reference source ↗", "参考資料 ↗"],
        "Chợ gốm trong làng cổ Bát Tràng. Vị trí tham khảo từ ghim bản đồ của Cổng thông tin du lịch Gia Lâm.": ["Pottery market in Bát Tràng’s old village. Reference position from Gia Lam Tourism Portal’s published map marker.", "バッチャン旧村の陶器市場。位置はザーラム観光案内の公開マーカーによる参考値です。"],
        "Đình làng bên sông Hồng. Vị trí tham khảo theo ảnh có tọa độ chụp tại đình; chưa xác minh lối vào.": ["Communal house beside the Red River. Reference position from a geotagged photograph taken at the site; the entrance is unverified.", "紅河沿いの集会所。位置は現地で撮影された位置情報付き写真を参考にしています。入口は未確認です。"],
        "Lò bầu cổ tại thôn 3, Bát Tràng. Vị trí tham khảo từ ghim bản đồ của Cổng thông tin du lịch Gia Lâm.": ["Traditional kiln in Hamlet 3, Bát Tràng. Reference position from Gia Lam Tourism Portal’s published map marker.", "バッチャン第3集落の伝統的な窯。位置はザーラム観光案内の公開マーカーによる参考値です。"],
        "Bảo tàng Gốm tại số 28 đường Làng cổ Bát Tràng. Vị trí bản đồ mở đã đối chiếu với bản đồ của bảo tàng.": ["Ceramics Museum at 28 Lang Co Bat Trang Road. Open map position cross-checked with the museum’s own map.", "ランコーバッチャン通り28番の陶器博物館。公開地図の位置を博物館の地図と照合しています。"],
        "Chùa Kim Trúc tại Bát Tràng. Vị trí tham khảo từ ghim bản đồ của Cổng thông tin du lịch Gia Lâm.": ["Kim Truc Pagoda in Bát Tràng. Reference position from Gia Lam Tourism Portal’s published map marker.", "バッチャンの金竹寺。位置はザーラム観光案内の公開マーカーによる参考値です。"],
        "Bảo tàng Gốm Bát Tràng": ["Bát Tràng Ceramics Museum", "バッチャン陶器博物館"],
        "Chùa Kim Trúc (Bát Tràng)": ["Kim Truc Pagoda (Bát Tràng)", "金竹寺（バッチャン）"]
    };
    const supported = ["vi", "en", "ja"];
    const storageKey = "bat-trang-visitor-language-v1";
    const countryLanguages = { VN: "vi", JP: "ja", US: "en", GB: "en", AU: "en" };
    const names = { vi: "Tiếng Việt", en: "English", ja: "日本語" };
    function detectLanguage(languages) {
        for (const tag of languages || []) {
            const code = String(tag).toLowerCase().split(/[-_]/)[0];
            if (supported.includes(code)) return code;
        }
        return "en";
    }
    let preference = null;
    try { preference = JSON.parse(localStorage.getItem(storageKey)); } catch { /* Private browsing. */ }
    let language = supported.includes(preference?.language)
        ? preference.language : detectLanguage(navigator.languages || [navigator.language]);
    let country = Object.hasOwn(countryLanguages, preference?.country) ? preference.country : "";

    function translate(source, values = {}, locale = language) {
        if (source == null) return "";
        const row = Object.hasOwn(messages, source) ? messages[source] : null;
        const text = locale === "vi" || !row ? String(source) : row[locale === "ja" ? 1 : 0];
        return text.replace(/\{(\w+)\}/g, (match, key) => Object.hasOwn(values, key) ? String(values[key]) : match);
    }
    function apply(root = document, locale = language) {
        root.querySelectorAll("[data-i18n]").forEach(element => {
            element.textContent = translate(element.dataset.i18n, {}, locale);
        });
        for (const attribute of ["aria-label", "placeholder", "alt", "title"]) {
            root.querySelectorAll(`[data-i18n-${attribute}]`).forEach(element => {
                element.setAttribute(attribute, translate(element.getAttribute(`data-i18n-${attribute}`), {}, locale));
            });
        }
    }
    function setLanguage(next, nextCountry = country) {
        if (!supported.includes(next)) return false;
        language = next;
        country = Object.hasOwn(countryLanguages, nextCountry) ? nextCountry : "";
        let saved = true;
        try { localStorage.setItem(storageKey, JSON.stringify({ language, country })); }
        catch { saved = false; }
        document.documentElement.lang = language;
        apply();
        const select = document.getElementById("language");
        if (select) select.value = language;
        window.dispatchEvent(new CustomEvent("visitorlanguagechange"));
        return saved;
    }
    function init() {
        document.documentElement.lang = language;
        apply();
        const select = document.getElementById("language");
        if (select) select.value = language;
        const dialog = document.getElementById("languageDialog");
        if (!dialog) return;
        const countrySelect = document.getElementById("visitorCountry");
        let pendingLanguage = language;
        function preview() {
            dialog.lang = pendingLanguage;
            apply(dialog, pendingLanguage);
            dialog.querySelectorAll("[data-language-choice]").forEach(button => {
                button.setAttribute("aria-pressed", String(button.dataset.languageChoice === pendingLanguage));
            });
        }
        function open() {
            pendingLanguage = language;
            countrySelect.value = country;
            preview();
            dialog.showModal();
        }
        dialog.querySelectorAll("[data-language-choice]").forEach(button => {
            button.addEventListener("click", () => { pendingLanguage = button.dataset.languageChoice; preview(); });
        });
        countrySelect.addEventListener("change", () => {
            pendingLanguage = Object.hasOwn(countryLanguages, countrySelect.value)
                ? countryLanguages[countrySelect.value] : pendingLanguage;
            preview();
        });
        document.getElementById("confirmLanguage").addEventListener("click", () => {
            const saved = setLanguage(pendingLanguage, countrySelect.value);
            dialog.close();
            document.getElementById("languagePreferenceStatus").textContent = saved ? "" :
                translate("Trình duyệt không cho lưu lựa chọn; bạn vẫn dùng được ngôn ngữ này trong lần mở hiện tại.");
        });
        document.getElementById("changeLanguageButton").addEventListener("click", open);
        if (!supported.includes(preference?.language)) open();
    }
    return { t: translate, apply, init, setLanguage, detectLanguage, names,
        get language() { return language; } };
})();
