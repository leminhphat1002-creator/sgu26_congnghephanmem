"""REST API cho module POI."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.auth import require_admin
from app.core.db import get_db
from app.modules.admin.repository import AdminRepository
from app.modules.poi import repository, service
from app.modules.poi.schemas import LocationCreate, LocationRead, LocationUpdate

router = APIRouter(tags=["poi"])

DatabaseSession = Annotated[Session, Depends(get_db)]


@router.get("/locations", response_model=list[LocationRead])
def list_locations(
    session: DatabaseSession,
    limit: int = Query(default=100, ge=1, le=500),
    name: str | None = Query(default=None),
):
    """Lấy danh sách địa điểm và tìm kiếm không phân biệt hoa thường."""

    locations = repository.list_locations(session, limit=limit)

    if name is not None and name.strip():
        keyword = name.strip().casefold()

        locations = [location for location in locations if keyword in location.name.casefold()]

    return locations


@router.post(
    "/locations",
    response_model=LocationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_location(
    data: LocationCreate,
    session: DatabaseSession,
    identity: Annotated[dict, Depends(require_admin)],
):
    """Tạo địa điểm mới."""
    if (data.latitude is None) != (data.longitude is None):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Latitude và longitude phải cùng có hoặc cùng không có.",
        )

    try:
        location = repository.create_location(
            session,
            **data.model_dump(),
        )
        AdminRepository(session).record(identity["username"], "create_location", str(location.id))
        return location
    except Exception:
        session.rollback()
        raise


@router.get("/locations/nearby")
def find_nearby_locations(
    session: DatabaseSession,
    latitude: float = Query(ge=-90, le=90),
    longitude: float = Query(ge=-180, le=180),
    radius: float = Query(default=500, gt=0, le=100000),
):
    """Tìm các địa điểm gần tọa độ GPS."""
    try:
        results = service.find_nearby(
            session,
            latitude,
            longitude,
            search_radius_meters=radius,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return [
        {
            "location": LocationRead.model_validate(location),
            "distance_meters": round(distance, 2),
            "should_activate": service.choose_activation(
                distance,
                location.radius,
            ),
        }
        for location, distance in results
    ]


@router.get("/locations/{location_id}", response_model=LocationRead)
def get_location(
    location_id: int,
    session: DatabaseSession,
):
    """Lấy thông tin một địa điểm."""
    location = repository.get_location(session, location_id)

    if location is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy địa điểm.",
        )

    return location


@router.put("/locations/{location_id}", response_model=LocationRead)
def update_location(
    location_id: int,
    data: LocationUpdate,
    session: DatabaseSession,
    identity: Annotated[dict, Depends(require_admin)],
):
    """Cập nhật địa điểm."""
    changes = data.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cần cung cấp ít nhất một trường để cập nhật.",
        )

    for field in ("name", "radius", "source", "is_ready"):
        if field in changes and changes[field] is None:
            raise HTTPException(422, f"{field} không được để trống.")
    existing = repository.get_location(session, location_id)
    if existing is not None:
        latitude = changes.get("latitude", existing.latitude)
        longitude = changes.get("longitude", existing.longitude)
        if (latitude is None) != (longitude is None):
            raise HTTPException(422, "Vĩ độ và kinh độ phải cùng có hoặc cùng không có.")

    try:
        location = repository.update_location(
            session,
            location_id,
            **changes,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    if location is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy địa điểm.",
        )

    AdminRepository(session).record(identity["username"], "update_location", str(location_id))
    return location


@router.delete(
    "/locations/{location_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_location(
    location_id: int,
    session: DatabaseSession,
    identity: Annotated[dict, Depends(require_admin)],
):
    """Xóa địa điểm."""
    deleted = repository.delete_location(session, location_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy địa điểm.",
        )

    AdminRepository(session).record(identity["username"], "delete_location", str(location_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
