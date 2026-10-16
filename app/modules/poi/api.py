"""Presentation API cho quản lý địa điểm và tìm POI gần GPS."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.poi.schemas import LocationCreate, LocationRead, NearbyResponse
from app.modules.poi.service import LocationService

router = APIRouter(tags=["poi"])
DbSession = Annotated[Session, Depends(get_db)]


@router.post("/locations", response_model=LocationRead, status_code=status.HTTP_201_CREATED)
def create_location(payload: LocationCreate, db: DbSession):
    return LocationService(db).create(payload)


@router.get("/locations", response_model=list[LocationRead])
def list_locations(db: DbSession, limit: int = Query(default=100, ge=1, le=500), offset: int = Query(default=0, ge=0)):
    return LocationService(db).list(limit, offset)


@router.get("/locations/{location_id}", response_model=LocationRead)
def get_location(location_id: int, db: DbSession):
    return LocationService(db).get(location_id)


@router.delete("/locations/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_location(location_id: int, db: DbSession):
    LocationService(db).delete(location_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/locations/nearby", response_model=NearbyResponse)
def find_nearby(
    db: DbSession,
    latitude: float = Query(ge=-90, le=90),
    longitude: float = Query(ge=-180, le=180),
    radius_m: float = Query(default=500, gt=0, le=100_000),
):
    items = LocationService(db).find_nearby(latitude, longitude, radius_m)
    return NearbyResponse(items=items, count=len(items), latitude=latitude, longitude=longitude, search_radius_m=radius_m)
