"""Dữ liệu minh họa Bát Tràng; không phải tọa độ khảo sát hay bài giới thiệu chính thức.

Chạy: python -m scripts.seed_bat_trang (sau alembic upgrade head).
Chạy lại chỉ bổ sung bản ghi thiếu, không ghi đè nội dung đã biên tập.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_sessionmaker
from app.modules.content.models import PoiNarration
from app.modules.poi.models import Location

SAMPLE_POIS = [
    (
        "Chợ gốm Bát Tràng",
        20.9784,
        105.9146,
        (
            "Chợ gốm là điểm dừng trong hành trình khám phá Bát Tràng. Hãy quan sát hình "
            "dáng, màu men và hoa văn trên các sản phẩm để cảm nhận sự đa dạng của đồ gốm. "
            "Khi mua hàng, bạn nên hỏi người bán về chất liệu, cách sử dụng và cách đóng "
            "gói. Đây là bài thuyết minh mẫu phục vụ đồ án. "
        ),
        "Bat Trang Pottery Market",
        (
            "The pottery market is a stop on this sample tour of Bat Trang. Look at the "
            "shapes, glazes and decorative patterns of the ceramics. Before buying, ask the "
            "seller about materials, intended use and protective packaging. This sample "
            "narration is prepared for a student project. "
        ),
        "バッチャン陶器市場",
        (
            "陶器市場は、バッチャンを巡るモデルコースの立ち寄り場所です。器の形、釉薬の色、模様を見比べてみましょう。購入するときは、素材、使い方、梱包方"
            "法をお店の人に確認してください。この文章は学生プロジェクト用のサンプルです。 "
        ),
    ),
    (
        "Đình làng Bát Tràng",
        20.9777,
        105.9138,
        (
            "Đình làng là một điểm tìm hiểu không gian văn hóa cộng đồng trong hành trình "
            "Bát Tràng. Khi tham quan, hãy giữ yên lặng, ăn mặc phù hợp và làm theo hướng "
            "dẫn tại chỗ. Chỉ chụp ảnh ở khu vực được cho phép. Bài giới thiệu này là nội "
            "dung mẫu, không thay thế thông tin của đơn vị quản lý di tích. "
        ),
        "Bat Trang Communal House",
        (
            "This stop introduces a communal cultural space on the sample Bat Trang tour. "
            "Please remain quiet, dress respectfully and follow instructions on site. Take "
            "photographs only where permitted. This sample introduction does not replace "
            "information provided by the site's management. "
        ),
        "バッチャン村の共同亭",
        (
            "このモデルコースでは、村の共同亭を通して地域の文化空間に触れます。静かに見学し、服装に配慮して現地の案内に従ってください。撮影は許可された場"
            "所で行いましょう。この紹介文はサンプルであり、施設の公式案内ではありません。 "
        ),
    ),
    (
        "Lò bầu cổ Bát Tràng",
        20.9788,
        105.9135,
        (
            "Điểm dừng lò bầu gợi mở câu chuyện về công đoạn nung gốm. Bạn có thể tìm hiểu "
            "mối liên hệ giữa nhiệt độ, nguyên liệu và màu men qua phần giới thiệu tại chỗ. "
            "Không chạm vào thiết bị hoặc đi vào khu vực hạn chế. Đây là nội dung minh họa; "
            "thông tin kỹ thuật cần được xác nhận với người hướng dẫn. "
        ),
        "Bat Trang Traditional Kiln",
        (
            "This sample stop introduces the firing stage of pottery making. Use the "
            "information available on site to explore how temperature, materials and glazes "
            "interact. Do not touch equipment or enter restricted areas. Technical details "
            "should be confirmed with a local guide. "
        ),
        "バッチャンの伝統的な窯",
        (
            "この立ち寄り場所では、陶器を焼く工程に注目します。温度、原料、釉薬の関係について、現地の説明を聞いてみましょう。設備に触れたり、立入禁止の場"
            "所に入ったりしないでください。技術的な情報は現地の案内人に確認してください。 "
        ),
    ),
    (
        "Không gian trưng bày gốm Bát Tràng",
        20.9795,
        105.9154,
        (
            "Không gian trưng bày trong tuyến mẫu giúp bạn quan sát đồ gốm từ góc nhìn hình "
            "khối và trang trí. Hãy chọn một sản phẩm và chú ý đến miệng, thân, đáy cùng "
            "cách phối màu. Không tự ý cầm hiện vật. Tên điểm dừng và tọa độ trong bản demo "
            "mang tính minh họa, cần xác minh trước khi sử dụng thực tế. "
        ),
        "Bat Trang Ceramics Display",
        (
            "This illustrative display stop invites you to study ceramic forms and "
            "decoration. Choose an object and observe its rim, body, base and colour "
            "combinations. Do not handle exhibits without permission. The stop name and "
            "coordinates in this demo must be verified before real-world use. "
        ),
        "バッチャン陶器の展示空間",
        (
            "この展示を想定したサンプル地点では、陶器の形と装飾を観察します。一つの器を選び、口、胴、底、色の組み合わせに注目しましょう。許可なく展示品に"
            "触れないでください。このデモの地点名と座標は、実際に使う前に確認が必要です。 "
        ),
    ),
    (
        "Không gian trải nghiệm làm gốm",
        20.9779,
        105.9152,
        (
            "Điểm trải nghiệm trong tuyến mẫu giới thiệu hoạt động tạo hình với đất sét. "
            "Trước khi tham gia, hãy hỏi về chi phí, thời gian và cách nhận sản phẩm. Làm "
            "theo hướng dẫn của người phụ trách để sử dụng dụng cụ an toàn. Đây là điểm "
            "minh họa cho đồ án, không phải thông tin đặt dịch vụ hay cam kết của một cơ sở "
            "cụ thể. "
        ),
        "Pottery Making Experience",
        (
            "This illustrative stop introduces shaping clay. Before joining an activity, "
            "ask about the price, duration and how finished pieces are collected. Follow "
            "the instructor's guidance when using tools. This student demo does not "
            "represent a booking service or an offer from a specific workshop. "
        ),
        "陶芸体験スペース",
        (
            "このサンプル地点では、粘土を使った成形体験を紹介します。参加前に料金、所要時間、作品の受け取り方法を確認しましょう。道具は担当者の指示に従っ"
            "て安全に使ってください。"
            "このデモは、特定の工房の予約やサービスを提供するものではありません。 "
        ),
    ),
]


def seed(session: Session) -> None:
    """Bổ sung dữ liệu demo trong một giao dịch, không sửa dữ liệu cũ."""
    for name, lat, lon, vi, en_title, en, ja_title, ja in SAMPLE_POIS:
        location = session.scalar(
            select(Location).where(Location.source == "bat_trang_demo", Location.name == name)
        )
        if location is None:
            location = Location(
                name=name,
                latitude=lat,
                longitude=lon,
                radius=80,
                source="bat_trang_demo",
                is_ready=True,
                description_source="Dữ liệu demo — tọa độ và nội dung cần xác minh.",
            )
            session.add(location)
            session.flush()
        for language, title, content in (
            ("vi", name, vi),
            ("en", en_title, en),
            ("ja", ja_title, ja),
        ):
            existing = session.scalar(
                select(PoiNarration).where(
                    PoiNarration.location_id == location.id, PoiNarration.language == language
                )
            )
            if existing is None:
                session.add(
                    PoiNarration(
                        location_id=location.id, language=language, title=title, content=content
                    )
                )
    session.commit()


if __name__ == "__main__":
    with get_sessionmaker()() as session:
        seed(session)
    print("Seed complete: 5 demo POIs / 15 narrations; existing content preserved.")
