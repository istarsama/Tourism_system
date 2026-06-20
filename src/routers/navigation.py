"""
导航路由：/navigate（校园 Dijkstra）、/navigate/osm（全国 OSM 路网）
"""

import json
from datetime import datetime
from time import perf_counter

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from algorithms import dijkstra_search, plan_multi_point_route
from database import get_session
from models import NationalSpot, RouteCache
from schemas.navigation import (
    NavigateRequest,
    NavigateResponse,
    OSMNavigateRequest,
    OSMNavigateResponse,
)
from services.map_service import get_graph, get_osm_service
from loguru import logger

router = APIRouter(tags=["导航"])
OSM_ROUTE_CACHE_PREFIX = "osm:v3"


def _build_osm_route_cache_key(
    city: str,
    transport: str,
    start_spot_id: int,
    end_spot_id: int,
    via_spot_ids: list[int] | None = None,
) -> str:
    route_spot_ids = [start_spot_id, *(via_spot_ids or []), end_spot_id]
    return f"{OSM_ROUTE_CACHE_PREFIX}:{city}:{transport}:{','.join(map(str, route_spot_ids))}"


def _get_cached_osm_route(session: Session, cache_key: str) -> dict | None:
    cache = session.exec(select(RouteCache).where(RouteCache.cache_key == cache_key)).first()
    if cache is None:
        return None

    if cache.expires_at is not None and cache.expires_at <= datetime.now():
        session.delete(cache)
        session.commit()
        return None

    try:
        route = json.loads(cache.route_json)
        required_fields = {
            "city",
            "transport",
            "start_spot_id",
            "end_spot_id",
            "node_ids",
            "path_coords",
            "total_distance_m",
            "segment_count",
            "segment_distances_m",
            "estimated_duration_s",
            "legs",
        }
        if not required_fields.issubset(route):
            raise ValueError("缓存缺少必要字段")
        return route
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        logger.warning("OSM 路线缓存损坏，将删除后重新计算: cache_key={} error={}", cache_key, exc)
        session.delete(cache)
        session.commit()
        return None


def _save_osm_route_cache(session: Session, cache_key: str, response: dict) -> None:
    try:
        cache = session.exec(select(RouteCache).where(RouteCache.cache_key == cache_key)).first()
        if cache is None:
            cache = RouteCache(cache_key=cache_key)

        cache.mode = "osm"
        cache.provider = "osmnx"
        cache.distance_m = float(response["total_distance_m"])
        cache.duration_s = float(response["estimated_duration_s"])
        cache.route_json = json.dumps(response, ensure_ascii=False)
        cache.created_at = datetime.now()
        cache.expires_at = None
        session.add(cache)
        session.commit()
    except Exception as exc:
        session.rollback()
        logger.warning("OSM 路线结果缓存写入失败，不影响本次导航: cache_key={} error={}", cache_key, exc)


@router.post("/navigate", response_model=NavigateResponse)
def navigate(request: NavigateRequest):
    """
    校园智能导航接口。
    支持单点（A→B）和多点环线规划（A→多个目标→A），可选步行/自行车、最短距离/最短时间。
    """
    graph = get_graph()
    if not graph:
        raise HTTPException(status_code=500, detail="地图未初始化")

    path_ids = []
    cost = 0.0

    if request.start_id not in graph.spots:
        raise HTTPException(status_code=404, detail="起点不存在")

    if request.via_ids:
        target_ids = list(request.via_ids)
        if request.end_id is not None:
            target_ids.append(request.end_id)

        for target_id in target_ids:
            if target_id not in graph.spots:
                raise HTTPException(status_code=404, detail=f"目标点 ID {target_id} 不存在")
        path_ids, cost = plan_multi_point_route(
            graph, request.start_id, target_ids, request.strategy, request.transport
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
    途经点严格按 via_spot_ids 的输入顺序经过。
    """
    started_at = perf_counter()
    logger.info(
        "收到 OSM 导航请求 start_spot_id={} via_spot_ids={} end_spot_id={} transport={}",
        request.start_spot_id,
        request.via_spot_ids,
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

    route_spot_ids = [request.start_spot_id, *request.via_spot_ids, request.end_spot_id]
    if len(route_spot_ids) != len(set(route_spot_ids)):
        raise HTTPException(status_code=400, detail="起点、途经点和终点不能重复")

    via_spots = []
    for index, spot_id in enumerate(request.via_spot_ids, start=1):
        spot = session.get(NationalSpot, spot_id)
        if not spot or not spot.is_active:
            raise HTTPException(status_code=404, detail=f"途经点 {index} 全国景点不存在")
        via_spots.append(spot)

    if start_spot.city != end_spot.city:
        raise HTTPException(
            status_code=400,
            detail=f"当前仅支持同城市景点之间的 OSM 导航: 起点城市={start_spot.city}, 终点城市={end_spot.city}",
        )

    for index, via_spot in enumerate(via_spots, start=1):
        if via_spot.city != start_spot.city:
            raise HTTPException(
                status_code=400,
                detail=(
                    "当前仅支持同城市景点之间的 OSM 导航: "
                    f"起点城市={start_spot.city}, 途经点{index}城市={via_spot.city}"
                ),
            )

    logger.info(
        "OSM 导航景点解析成功 city={} transport={} start={} vias={} end={}",
        start_spot.city,
        request.transport,
        start_spot.name,
        [spot.name for spot in via_spots],
        end_spot.name,
    )

    route_cache_key = _build_osm_route_cache_key(
        start_spot.city,
        request.transport,
        request.start_spot_id,
        request.end_spot_id,
        request.via_spot_ids,
    )
    cached_response = _get_cached_osm_route(session, route_cache_key)
    if cached_response is not None:
        logger.info(
            "命中 OSM 路线结果缓存 cache_key={} elapsed_ms={:.2f}",
            route_cache_key,
            (perf_counter() - started_at) * 1000,
        )
        return cached_response

    logger.info("未命中 OSM 路线结果缓存 cache_key={}", route_cache_key)
    osm_service = get_osm_service()
    route_spots = [start_spot, *via_spots, end_spot]
    leg_results = []
    try:
        for leg_index, (leg_start, leg_end) in enumerate(
            zip(route_spots, route_spots[1:]), start=1
        ):
            try:
                leg_results.append(
                    osm_service.route_planning(
                        city=start_spot.city,
                        start_lat=leg_start.latitude,
                        start_lng=leg_start.longitude,
                        end_lat=leg_end.latitude,
                        end_lng=leg_end.longitude,
                        transport=request.transport,
                    )
                )
            except ValueError as exc:
                raise ValueError(
                    f"第 {leg_index} 段（{leg_start.name} → {leg_end.name}）规划失败: {exc}"
                ) from exc
    except ValueError as exc:
        elapsed_ms = (perf_counter() - started_at) * 1000
        logger.warning(
            "OSM 导航失败 city={} transport={} route_spot_ids={} error={} elapsed_ms={:.2f}",
            start_spot.city,
            request.transport,
            route_spot_ids,
            exc,
            elapsed_ms,
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        elapsed_ms = (perf_counter() - started_at) * 1000
        logger.exception(
            "OSM 导航出现未预期异常 city={} transport={} route_spot_ids={} elapsed_ms={:.2f}",
            start_spot.city,
            request.transport,
            route_spot_ids,
            elapsed_ms,
        )
        raise HTTPException(status_code=500, detail="OSM 导航服务异常，请稍后重试") from exc

    node_ids = []
    path_coords = []
    segment_distances_m = []
    total_distance_m = 0.0
    estimated_duration_s = 0.0
    segment_count = 0
    for result in leg_results:
        leg_node_ids = list(result.get("node_ids", []))
        leg_path_coords = list(result.get("path_coords", []))
        if node_ids and leg_node_ids and node_ids[-1] == leg_node_ids[0]:
            leg_node_ids = leg_node_ids[1:]
        if path_coords and leg_path_coords and path_coords[-1] == leg_path_coords[0]:
            leg_path_coords = leg_path_coords[1:]
        node_ids.extend(leg_node_ids)
        path_coords.extend(leg_path_coords)

        leg_segment_distances = [float(d) for d in result.get("segment_distances_m", [])]
        segment_distances_m.extend(leg_segment_distances)
        segment_count += int(result.get("segment_count", len(leg_segment_distances)))
        total_distance_m += float(result.get("total_distance_m", 0.0))
        estimated_duration_s += float(result.get("estimated_duration_s", 0.0))

    response = {
        "city": start_spot.city,
        "transport": request.transport,
        "start_spot_id": request.start_spot_id,
        "end_spot_id": request.end_spot_id,
        "via_spot_ids": request.via_spot_ids,
        "node_ids": node_ids,
        "path_coords": path_coords,
        "total_distance_m": total_distance_m,
        "segment_count": segment_count,
        "segment_distances_m": segment_distances_m,
        "estimated_duration_s": estimated_duration_s,
        "legs": [
            {
                "start_spot_id": leg_start.id,
                "end_spot_id": leg_end.id,
                "total_distance_m": float(result.get("total_distance_m", 0.0)),
                "segment_count": int(
                    result.get("segment_count", len(result.get("segment_distances_m", [])))
                ),
                "estimated_duration_s": float(result.get("estimated_duration_s", 0.0)),
            }
            for (leg_start, leg_end), result in zip(
                zip(route_spots, route_spots[1:]), leg_results
            )
        ],
    }
    _save_osm_route_cache(session, route_cache_key, response)

    elapsed_ms = (perf_counter() - started_at) * 1000
    logger.info(
        "OSM 导航完成 city={} transport={} route_spot_ids={} legs={} nodes={} distance={}m eta={}s elapsed_ms={:.2f}",
        response["city"],
        response["transport"],
        route_spot_ids,
        len(leg_results),
        len(response["node_ids"]),
        response["total_distance_m"],
        response["estimated_duration_s"],
        elapsed_ms,
    )
    return response
