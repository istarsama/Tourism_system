"""
地图路由：/graph、/map/campus-graph、/map/mode、/map/national-spots
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlmodel import Session, select

from database import get_session
from models import Diary, MapConfig, NationalSpot, NationalSpotXHSNote
from schemas.map import MapModeResponse, NationalSpotMapResponse
from services.map_service import get_graph

router = APIRouter(tags=["地图"])

# ────────────────────────────── 地图配置常量 ──────────────────────────────

DEFAULT_MAP_CONFIGS = {
    "campus": {
        "center_lat": 39.9629,
        "center_lng": 116.3520,
        "zoom_level": 16,
        "map_provider": "campus_canvas",
    },
    "national": {
        "center_lat": 35.8617,
        "center_lng": 104.1954,
        "zoom_level": 5,
        "map_provider": "osm",
    },
}

MAP_RENDERING_HINTS = {
    "campus": {
        "supports_slippy_map": False,
        "coordinate_system": "campus_pixel",
        "tile_layer": None,
    },
    "national": {
        "supports_slippy_map": True,
        "coordinate_system": "wgs84",
        "tile_layer": {
            "tile_url": "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
            "attribution": "&copy; OpenStreetMap contributors",
            "min_zoom": 3,
            "max_zoom": 19,
            "subdomains": ["a", "b", "c"],
            "usage_tier": "demo",
            "usage_note": "仅建议开发或课堂演示环境直连公开 OSM 瓦片；生产环境请替换为自建或商用瓦片服务。",
            "requires_backend_proxy": False,
        },
    },
}


def ensure_default_map_configs(session: Session) -> None:
    """确保数据库中存在默认地图配置，启动时调用一次即可。"""
    created = False
    for scope, cfg in DEFAULT_MAP_CONFIGS.items():
        if session.exec(select(MapConfig).where(MapConfig.scope == scope)).first():
            continue
        session.add(MapConfig(scope=scope, **cfg))
        created = True
    if created:
        session.commit()


# ────────────────────────────── 路由定义 ──────────────────────────────


@router.get("/graph")
def get_graph_data():
    """返回前端渲染校园地图所需的节点和边数据。"""
    graph = get_graph()
    if not graph:
        raise HTTPException(status_code=500, detail="地图数据未加载")

    nodes_data = [vars(spot) for spot in graph.spots.values()]

    edges_data = []
    seen_edges = set()
    for u_id, roads in graph.adj.items():
        for road in roads:
            pair = tuple(sorted((road.u, road.v)))
            if pair not in seen_edges:
                edges_data.append({"u": road.u, "v": road.v, "distance": road.distance})
                seen_edges.add(pair)

    return {"nodes": nodes_data, "edges": edges_data}


@router.get("/map/campus-graph")
def get_campus_graph():
    return get_graph_data()


@router.get("/map/mode", response_model=MapModeResponse)
def get_map_mode(
    scope: str = Query(default="campus", pattern="^(campus|national)$"),
    session: Session = Depends(get_session),
):
    config = session.exec(select(MapConfig).where(MapConfig.scope == scope)).first()
    if not config:
        default_cfg = DEFAULT_MAP_CONFIGS[scope]
        config = MapConfig(scope=scope, **default_cfg)
        session.add(config)
        session.commit()
        session.refresh(config)

    render_hint = MAP_RENDERING_HINTS[scope]
    return {
        "scope": config.scope,
        "center_lat": config.center_lat,
        "center_lng": config.center_lng,
        "zoom_level": config.zoom_level,
        "map_provider": config.map_provider,
        "data_source": "campus_graph" if scope == "campus" else "national_spot",
        "supports_slippy_map": render_hint["supports_slippy_map"],
        "coordinate_system": render_hint["coordinate_system"],
        "tile_layer": render_hint["tile_layer"],
    }


@router.get("/map/national-spots", response_model=List[NationalSpotMapResponse])
def get_national_spots(
    city: Optional[str] = None,
    spot_type: Optional[str] = Query(default=None, alias="type"),
    limit: int = Query(default=200, ge=1, le=500),
    session: Session = Depends(get_session),
):
    """返回全国景点地图点位及其小红书预览元数据。"""
    query = select(NationalSpot).where(NationalSpot.is_active == True)
    if city:
        query = query.where(NationalSpot.city == city)
    if spot_type:
        query = query.where(NationalSpot.type == spot_type)

    spots = session.exec(
        query.order_by(NationalSpot.rating.desc(), NationalSpot.name).limit(limit)
    ).all()
    if not spots:
        return []

    spot_ids = [s.id for s in spots if s.id is not None]

    diary_count_map: dict[int, int] = {}
    if spot_ids:
        rows = session.exec(
            select(Diary.national_spot_id, func.count(Diary.id))
            .where(
                Diary.scope == "national",
                Diary.national_spot_id.in_(spot_ids),
            )
            .group_by(Diary.national_spot_id)
        ).all()
        diary_count_map = {
            int(nid): int(cnt)
            for nid, cnt in rows
            if nid is not None
        }

    note_preview_map: dict[int, list[dict]] = {}
    if spot_ids:
        preview_rows = session.exec(
            select(NationalSpotXHSNote)
            .where(NationalSpotXHSNote.national_spot_id.in_(spot_ids))
            .order_by(
                NationalSpotXHSNote.national_spot_id,
                NationalSpotXHSNote.rank_order,
                NationalSpotXHSNote.id,
            )
        ).all()
        for preview in preview_rows:
            note_preview_map.setdefault(preview.national_spot_id, []).append(
                {
                    "note_id": preview.xhs_note_id,
                    "title": preview.title,
                    "content_preview": preview.content_preview,
                    "thumbnail_url": preview.thumbnail_url,
                    "xhs_url": preview.xhs_url,
                    "author_name": preview.author_name,
                    "author_id": preview.author_id,
                    "likes": preview.liked_count,
                }
            )

    return [
        {
            "id": spot.id,
            "name": spot.name,
            "type": spot.type,
            "latitude": spot.latitude,
            "longitude": spot.longitude,
            "description": spot.description,
            "city": spot.city,
            "province": spot.province,
            "flower_type": spot.flower_type,
            "best_season": spot.best_season,
            "rating": spot.rating,
            "diary_count": diary_count_map.get(spot.id, 0),
            "diary_api": f"/diaries/spot/{spot.id}?scope=national",
            "xhs_query": spot.xhs_query,
            "xhs_note_count": spot.xhs_note_count,
            "xhs_fetch_status": spot.xhs_fetch_status,
            "xhs_fetch_message": spot.xhs_fetch_message,
            "xhs_cookie_needs_refresh": spot.xhs_cookie_needs_refresh,
            "xhs_last_fetched_at": spot.xhs_last_fetched_at,
            "xhs_notes_preview": note_preview_map.get(spot.id, []),
        }
        for spot in spots
    ]
