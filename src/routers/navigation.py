"""
导航路由：/navigate（校园 Dijkstra）、/navigate/osm（全国 OSM 路网）
"""

from time import perf_counter

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from algorithms import dijkstra_search, plan_multi_point_route
from database import get_session
from models import NationalSpot
from schemas.navigation import (
    NavigateRequest,
    NavigateResponse,
    OSMNavigateRequest,
    OSMNavigateResponse,
)
from services.map_service import get_graph, get_osm_service
from loguru import logger

router = APIRouter(tags=["导航"])


@router.post("/navigate", response_model=NavigateResponse)
def navigate(request: NavigateRequest):
    """
    校园智能导航接口。
    支持单点（A→B）和多点贪心规划（A→B→C→…），可选步行/自行车、最短距离/最短时间。
    """
    graph = get_graph()
    if not graph:
        raise HTTPException(status_code=500, detail="地图未初始化")

    path_ids = []
    cost = 0.0

    if request.via_ids:
        for vid in request.via_ids:
            if vid not in graph.spots:
                raise HTTPException(status_code=404, detail=f"途经点 ID {vid} 不存在")
        path_ids, cost = plan_multi_point_route(
            graph, request.start_id, request.via_ids, request.strategy, request.transport
        )
    elif request.end_id is not None:
        if request.end_id not in graph.spots:
            raise HTTPException(status_code=404, detail="终点不存在")
        path_ids, cost = dijkstra_search(
            graph, request.start_id, request.end_id, request.strategy, request.transport
        )
    else:
        raise HTTPException(status_code=400, detail="必须提供 终点(end_id) 或 途经点列表(via_ids)")

    if not path_ids:
        raise HTTPException(status_code=400, detail="无法规划路径（可能是孤岛节点或无法到达）")

    path_names = [graph.get_spot_name(pid) for pid in path_ids]
    path_coords = [
        [graph.spots[pid].x, graph.spots[pid].y] if pid in graph.spots else [0, 0]
        for pid in path_ids
    ]
    unit = "米" if request.strategy == "dist" else "秒"

    return {
        "path_ids": path_ids,
        "path_names": path_names,
        "path_coords": path_coords,
        "total_cost": round(cost, 1),
        "cost_unit": unit,
    }


@router.post("/navigate/osm", response_model=OSMNavigateResponse)
def navigate_osm(request: OSMNavigateRequest, session: Session = Depends(get_session)):
    """
    全国 OSM 路网导航接口（同城景点间真实路网规划）。
    """
    started_at = perf_counter()
    logger.info(
        "收到 OSM 导航请求 start_spot_id={} end_spot_id={} transport={}",
        request.start_spot_id,
        request.end_spot_id,
        request.transport,
    )

    if request.transport not in {"walk", "bike"}:
        raise HTTPException(status_code=400, detail="transport 仅支持 'walk' 或 'bike'")

    start_spot = session.get(NationalSpot, request.start_spot_id)
    if not start_spot or not start_spot.is_active:
        raise HTTPException(status_code=404, detail="起点全国景点不存在")

    end_spot = session.get(NationalSpot, request.end_spot_id)
    if not end_spot or not end_spot.is_active:
        raise HTTPException(status_code=404, detail="终点全国景点不存在")

    if start_spot.city != end_spot.city:
        raise HTTPException(
            status_code=400,
            detail=f"当前仅支持同城市景点之间的 OSM 导航: 起点城市={start_spot.city}, 终点城市={end_spot.city}",
        )

    logger.info(
        "OSM 导航景点解析成功 city={} transport={} start={}({},{}) end={}({},{})",
        start_spot.city,
        request.transport,
        start_spot.name,
        start_spot.latitude,
        start_spot.longitude,
        end_spot.name,
        end_spot.latitude,
        end_spot.longitude,
    )

    osm_service = get_osm_service()
    try:
        result = osm_service.route_planning(
            city=start_spot.city,
            start_lat=start_spot.latitude,
            start_lng=start_spot.longitude,
            end_lat=end_spot.latitude,
            end_lng=end_spot.longitude,
            transport=request.transport,
        )
    except ValueError as exc:
        elapsed_ms = (perf_counter() - started_at) * 1000
        logger.warning(
            "OSM 导航失败 city={} transport={} start_spot_id={} end_spot_id={} error={} elapsed_ms={:.2f}",
            start_spot.city,
            request.transport,
            request.start_spot_id,
            request.end_spot_id,
            exc,
            elapsed_ms,
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        elapsed_ms = (perf_counter() - started_at) * 1000
        logger.exception(
            "OSM 导航出现未预期异常 city={} transport={} start_spot_id={} end_spot_id={} elapsed_ms={:.2f}",
            start_spot.city,
            request.transport,
            request.start_spot_id,
            request.end_spot_id,
            elapsed_ms,
        )
        raise HTTPException(status_code=500, detail="OSM 导航服务异常，请稍后重试") from exc

    segment_distances_m = [float(d) for d in result.get("segment_distances_m", [])]
    segment_count = int(result.get("segment_count", len(segment_distances_m)))
    estimated_duration_s = float(result.get("estimated_duration_s", 0.0))

    response = {
        "city": result["city"],
        "transport": result["transport"],
        "start_spot_id": request.start_spot_id,
        "end_spot_id": request.end_spot_id,
        "node_ids": result["node_ids"],
        "path_coords": result["path_coords"],
        "total_distance_m": result["total_distance_m"],
        "segment_count": segment_count,
        "segment_distances_m": segment_distances_m,
        "estimated_duration_s": estimated_duration_s,
    }

    elapsed_ms = (perf_counter() - started_at) * 1000
    logger.info(
        "OSM 导航完成 city={} transport={} start=({}, {}) end=({}, {}) nodes={} distance={}m eta={}s elapsed_ms={:.2f}",
        response["city"],
        response["transport"],
        start_spot.latitude,
        start_spot.longitude,
        end_spot.latitude,
        end_spot.longitude,
        len(response["node_ids"]),
        response["total_distance_m"],
        response["estimated_duration_s"],
        elapsed_ms,
    )
    return response
