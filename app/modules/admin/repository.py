"""Truy vấn dữ liệu quản trị và thống kê SQLite."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import Date, cast, delete, func, select
from sqlalchemy.orm import Session

from app.modules.admin.models import ActivityEvent, AdminSession, AdminUser
from app.modules.content.models import PoiNarration
from app.modules.poi.models import Location


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class AdminRepository:
    def __init__(self, session: Session):
        self.session = session

    def user(self, username: str):
        return self.session.scalar(select(AdminUser).where(AdminUser.username == username))

    def create_session(self, token_hash: str, user_id: int, csrf_token: str):
        self.session.execute(delete(AdminSession).where(AdminSession.expires_at <= utcnow()))
        self.session.add(
            AdminSession(
                token_hash=token_hash,
                user_id=user_id,
                csrf_token=csrf_token,
                expires_at=utcnow() + timedelta(hours=8),
            )
        )
        self.session.commit()

    def identity(self, token_hash: str) -> dict | None:
        row = self.session.execute(
            select(AdminUser.username, AdminSession.csrf_token)
            .join(AdminSession, AdminSession.user_id == AdminUser.id)
            .where(AdminSession.token_hash == token_hash, AdminSession.expires_at > utcnow())
        ).first()
        return {"username": row.username, "csrf_token": row.csrf_token} if row else None

    def revoke(self, token_hash: str):
        self.session.execute(delete(AdminSession).where(AdminSession.token_hash == token_hash))
        self.session.commit()

    def record(self, actor: str, action: str, target: str = "", status: str = "ok"):
        self.session.add(
            ActivityEvent(
                created_at=utcnow(), actor=actor, action=action, target=target[:255], status=status
            )
        )
        self.session.commit()

    def locations(self) -> list[dict]:
        rows = self.session.scalars(select(Location).order_by(Location.id))
        languages = {}
        for row in self.session.scalars(select(PoiNarration)):
            languages.setdefault(row.location_id, []).append(row.language)
        return [
            {
                "id": row.id,
                "name": row.name,
                "latitude": row.latitude,
                "longitude": row.longitude,
                "radius": row.radius,
                "description_source": row.description_source,
                "is_ready": row.is_ready,
                "languages": languages.get(row.id, []),
            }
            for row in rows
        ]

    def narrations(self, location_id: int) -> list[dict]:
        return [
            {"language": row.language, "title": row.title, "content": row.content}
            for row in self.session.scalars(
                select(PoiNarration).where(PoiNarration.location_id == location_id)
            )
        ]

    def save_narration(self, location_id: int, language: str, title: str, content: str):
        row = self.session.scalar(
            select(PoiNarration).where(
                PoiNarration.location_id == location_id, PoiNarration.language == language
            )
        )
        if row is None:
            row = PoiNarration(
                location_id=location_id, language=language, title=title, content=content
            )
            self.session.add(row)
        else:
            row.title, row.content = title, content
        self.session.commit()

    def delete_narration(self, location_id: int, language: str) -> bool:
        result = self.session.execute(
            delete(PoiNarration).where(
                PoiNarration.location_id == location_id, PoiNarration.language == language
            )
        )
        self.session.commit()
        return bool(result.rowcount)

    def dashboard(self) -> dict:
        def count(statement):
            return self.session.scalar(statement) or 0

        local_today = (utcnow() + timedelta(hours=7)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        today = local_today - timedelta(hours=7)
        local_start = local_today - timedelta(days=6)
        start = today - timedelta(days=6)
        activity = self.session.scalars(
            select(ActivityEvent)
            .where(ActivityEvent.actor != "visitor")
            .order_by(ActivityEvent.id.desc())
            .limit(15)
        )
        if self.session.get_bind().dialect.name == "postgresql":
            day_expression = cast(ActivityEvent.created_at + timedelta(hours=7), Date)
        else:
            day_expression = func.date(ActivityEvent.created_at, "+7 hours")
        daily = {
            str(day): total
            for day, total in self.session.execute(
                select(day_expression, func.count())
                .where(ActivityEvent.action == "narration", ActivityEvent.created_at >= start)
                .group_by(day_expression)
            ).all()
        }
        return {
            "locations": count(select(func.count()).select_from(Location)),
            "published": count(
                select(func.count())
                .select_from(Location)
                .where(
                    Location.is_ready.is_(True),
                    Location.id.in_(select(PoiNarration.location_id)),
                )
            ),
            "narrations": count(select(func.count()).select_from(PoiNarration)),
            "languages": dict(
                self.session.execute(
                    select(PoiNarration.language, func.count()).group_by(PoiNarration.language)
                ).all()
            ),
            "requests_today": count(
                select(func.count())
                .select_from(ActivityEvent)
                .where(ActivityEvent.action == "narration", ActivityEvent.created_at >= today)
            ),
            "daily": [
                {
                    "date": (local_start + timedelta(days=i)).date().isoformat(),
                    "count": daily.get((local_start + timedelta(days=i)).date().isoformat(), 0),
                }
                for i in range(7)
            ],
            "recent_activity": [
                {
                    "created_at": row.created_at.isoformat() + "Z",
                    "actor": row.actor,
                    "action": row.action,
                    "target": row.target,
                    "status": row.status,
                }
                for row in activity
            ],
            "timezone": "Asia/Bangkok",
        }
