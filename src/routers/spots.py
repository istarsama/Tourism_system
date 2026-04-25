"""
景点查询路由：/spots/list、/spots/search
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select
from thefuzz import process

from database import get_session
from models import NationalSpot
from services.map_service import get_graph

router = APIRouter(prefix="/spots", tags=["景点查询"])


@router.get("/list")
def get_all_spots():
    """返回所有校园景点（type='spot'）。"""
    graph = get_graph()
    if not graph:
        return []
    return [spot for spot in graph.spots.values() if spot.type == "spot"]


@router.get("/search")
def search_spots(
    query: str,
    limit: int = Query(default=5, ge=1, le=20),
    scope: str = Query(default="campus", pattern="^(campus|national)$"),
    city: Optional[str] = None,
    session: Session = Depends(get_session),
):
    """模糊搜索景点。scope=campus 搜索校园图内节点，scope=national 搜索全国景点库。"""
    if scope == "campus":
        graph = get_graph()
        if not graph:
            return []

        spot_map = {s.name: s.id for s in graph.spots.values() if s.type == "spot"}
        if not spot_map:
            return []

        matches = process.extract(query, spot_map.keys(), limit=limit)
        results = []
        for name, score in matches:
            if score > 40:
                spot_id = spot_map[name]
                spot_obj = graph.spots[spot_id]
                results.append(
                    {
                        "id": spot_id,
                        "name": name,
                        "score": score,
                        "x": spot_obj.x,
                        "y": spot_obj.y,
                        "scope": "campus",
                    }
                )
        return results

    # national 模式
    query_stmt = select(NationalSpot).where(NationalSpot.is_active == True)
    if city:
        query_stmt = query_stmt.where(NationalSpot.city == city)
    national_spots = session.exec(query_stmt).all()
    if not national_spots:
        return []

    label_to_spot = {f"{s.name}({s.city})": s for s in national_spots}
    matches = process.extract(query, label_to_spot.keys(), limit=limit)
    results = []
    for label, score in matches:
        if score <= 40:
            continue
        spot = label_to_spot[label]
        results.append(
            {
                "id": spot.id,
                "name": spot.name,
                "city": spot.city,
                "type": spot.type,
                "score": score,
                "latitude": spot.latitude,
                "longitude": spot.longitude,
                "xhs_note_count": spot.xhs_note_count,
                "xhs_fetch_status": spot.xhs_fetch_status,
                "xhs_cookie_needs_refresh": spot.xhs_cookie_needs_refresh,
                "scope": "national",
            }
        )
    return results
