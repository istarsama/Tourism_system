from __future__ import annotations

import zlib
from datetime import datetime
from typing import Dict

from sqlmodel import Session, select

from models import CampusGraph, Diary, NationalSpot, POI, POIAlias, POIGeometry


def normalize_alias(text: str) -> str:
    return " ".join(text.strip().lower().split())


def _ensure_alias(session: Session, poi_id: int, alias: str, source: str) -> bool:
    normalized = normalize_alias(alias)
    if not normalized:
        return False

    existing = session.exec(
        select(POIAlias).where(
            POIAlias.poi_id == poi_id,
            POIAlias.normalized_alias == normalized,
        )
    ).first()
    if existing:
        return False

    session.add(
        POIAlias(
            poi_id=poi_id,
            alias=alias,
            normalized_alias=normalized,
            source=source,
        )
    )
    return True


def _next_virtual_legacy_spot_id(session: Session, keyword: str) -> int:
    seed = 900000 + (zlib.crc32(keyword.encode("utf-8")) % 100000)
    candidate = seed

    for _ in range(1000):
        exists = session.exec(select(POI).where(POI.legacy_spot_id == candidate)).first()
        if not exists:
            return candidate
        candidate += 1

    raise ValueError("无法为虚拟景点分配 legacy_spot_id，请清理冲突数据后重试。")


def get_poi_by_name_or_alias(session: Session, keyword: str) -> POI | None:
    poi = session.exec(
        select(POI).where(
            POI.name == keyword,
            POI.is_active == True,
        )
    ).first()
    if poi:
        return poi

    normalized = normalize_alias(keyword)
    alias = session.exec(
        select(POIAlias).where(POIAlias.normalized_alias == normalized)
    ).first()
    if not alias:
        return None

    poi = session.get(POI, alias.poi_id)
    if poi and poi.is_active:
        return poi
    return None


def get_or_create_virtual_poi(
    session: Session,
    keyword: str,
    description: str = "网络搜索生成的虚拟景点",
) -> POI:
    existing = get_poi_by_name_or_alias(session, keyword)
    if existing:
        return existing

    poi = POI(
        name=keyword,
        poi_type="city_poi",
        source="xhs",
        source_ref=f"keyword:{normalize_alias(keyword)}",
        legacy_spot_id=_next_virtual_legacy_spot_id(session, keyword),
        description=description,
    )
    session.add(poi)
    session.flush()
    _ensure_alias(session, poi.id, keyword, source="xhs")
    session.commit()
    session.refresh(poi)
    return poi


def sync_campus_graph_to_poi(session: Session, graph: CampusGraph) -> Dict[str, int]:
    stats = {
        "poi_created": 0,
        "poi_updated": 0,
        "alias_added": 0,
        "geometry_created": 0,
        "geometry_updated": 0,
    }

    for spot in graph.spots.values():
        if spot.type != "spot":
            continue

        source_ref = str(spot.id)
        poi = session.exec(
            select(POI).where(
                POI.source == "campus",
                POI.source_ref == source_ref,
            )
        ).first()

        now = datetime.now()
        if not poi:
            poi = POI(
                name=spot.name,
                poi_type="campus_spot",
                source="campus",
                source_ref=source_ref,
                legacy_spot_id=spot.id,
                description=spot.desc or "",
                created_at=now,
                updated_at=now,
            )
            session.add(poi)
            session.flush()
            stats["poi_created"] += 1
        else:
            changed = False
            if poi.name != spot.name:
                poi.name = spot.name
                changed = True
            if (poi.description or "") != (spot.desc or ""):
                poi.description = spot.desc or ""
                changed = True
            if poi.legacy_spot_id != spot.id:
                poi.legacy_spot_id = spot.id
                changed = True
            if changed:
                poi.updated_at = now
                session.add(poi)
                stats["poi_updated"] += 1

        if _ensure_alias(session, poi.id, spot.name, source="campus_map"):
            stats["alias_added"] += 1

        geometry = session.exec(
            select(POIGeometry).where(
                POIGeometry.poi_id == poi.id,
                POIGeometry.geometry_type == "campus_pixel",
                POIGeometry.source == "campus_map",
            )
        ).first()

        if not geometry:
            session.add(
                POIGeometry(
                    poi_id=poi.id,
                    geometry_type="campus_pixel",
                    x_pixel=spot.x,
                    y_pixel=spot.y,
                    srid="LOCAL_PIXEL",
                    source="campus_map",
                    created_at=now,
                    updated_at=now,
                )
            )
            stats["geometry_created"] += 1
        else:
            if geometry.x_pixel != spot.x or geometry.y_pixel != spot.y:
                geometry.x_pixel = spot.x
                geometry.y_pixel = spot.y
                geometry.updated_at = now
                session.add(geometry)
                stats["geometry_updated"] += 1

    session.commit()
    return stats


def get_poi_for_campus_spot(session: Session, spot_id: int) -> POI | None:
    """按旧版校园 spot_id 找到对应 POI。"""
    return session.exec(
        select(POI).where(
            POI.source == "campus",
            POI.source_ref == str(spot_id),
            POI.is_active == True,
        )
    ).first()


def get_poi_for_national_spot(session: Session, national_spot_id: int) -> POI | None:
    """按全国景点 ID 找到对应 POI。"""
    return session.exec(
        select(POI).where(
            POI.source == "national_spot",
            POI.source_ref == str(national_spot_id),
            POI.is_active == True,
        )
    ).first()


def sync_national_spots_to_poi(session: Session) -> Dict[str, int]:
    """
    将 national_spot 映射到统一 POI。

    这个函数是 POI 统一迁移的兼容层：先建立稳定映射，再逐步让业务读写切到 poi_id。
    """
    stats = {
        "poi_created": 0,
        "poi_updated": 0,
        "alias_added": 0,
        "geometry_created": 0,
        "geometry_updated": 0,
    }
    now = datetime.now()
    spots = session.exec(select(NationalSpot)).all()

    for spot in spots:
        if spot.id is None:
            continue

        source_ref = str(spot.id)
        poi = session.exec(
            select(POI).where(
                POI.source == "national_spot",
                POI.source_ref == source_ref,
            )
        ).first()

        if not poi:
            poi = POI(
                name=spot.name,
                poi_type="national_spot",
                source="national_spot",
                source_ref=source_ref,
                description=spot.description or "",
                is_active=spot.is_active,
                created_at=now,
                updated_at=now,
            )
            session.add(poi)
            session.flush()
            stats["poi_created"] += 1
        else:
            changed = False
            if poi.name != spot.name:
                poi.name = spot.name
                changed = True
            if (poi.description or "") != (spot.description or ""):
                poi.description = spot.description or ""
                changed = True
            if poi.is_active != spot.is_active:
                poi.is_active = spot.is_active
                changed = True
            if changed:
                poi.updated_at = now
                session.add(poi)
                stats["poi_updated"] += 1

        if _ensure_alias(session, poi.id, spot.name, source="national_spot"):
            stats["alias_added"] += 1

        geometry = session.exec(
            select(POIGeometry).where(
                POIGeometry.poi_id == poi.id,
                POIGeometry.geometry_type == "wgs84_point",
                POIGeometry.source == "national_spot",
            )
        ).first()

        if not geometry:
            session.add(
                POIGeometry(
                    poi_id=poi.id,
                    geometry_type="wgs84_point",
                    longitude=spot.longitude,
                    latitude=spot.latitude,
                    srid="EPSG:4326",
                    source="national_spot",
                    created_at=now,
                    updated_at=now,
                )
            )
            stats["geometry_created"] += 1
        elif geometry.longitude != spot.longitude or geometry.latitude != spot.latitude:
            geometry.longitude = spot.longitude
            geometry.latitude = spot.latitude
            geometry.updated_at = now
            session.add(geometry)
            stats["geometry_updated"] += 1

    session.commit()
    return stats


def resolve_diary_poi_id(
    session: Session,
    *,
    scope: str,
    spot_id: int | None = None,
    national_spot_id: int | None = None,
) -> int | None:
    """根据旧字段解析统一 POI 主键。"""
    if scope == "campus" and spot_id is not None:
        poi = get_poi_for_campus_spot(session, spot_id)
        return poi.id if poi else None
    if scope == "national" and national_spot_id is not None:
        poi = get_poi_for_national_spot(session, national_spot_id)
        return poi.id if poi else None
    return None


def backfill_diary_poi_ids(session: Session) -> Dict[str, int]:
    """为历史日记补齐 poi_id。"""
    stats = {"updated": 0, "missing": 0}
    diaries = session.exec(select(Diary).where(Diary.poi_id == None)).all()  # noqa: E711
    for diary in diaries:
        poi_id = resolve_diary_poi_id(
            session,
            scope=diary.scope,
            spot_id=diary.spot_id,
            national_spot_id=diary.national_spot_id,
        )
        if poi_id is None:
            stats["missing"] += 1
            continue
        diary.poi_id = poi_id
        session.add(diary)
        stats["updated"] += 1

    if stats["updated"]:
        session.commit()
    return stats
