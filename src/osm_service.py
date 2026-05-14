from __future__ import annotations

from functools import lru_cache
from time import perf_counter
from typing import TypedDict

import networkx as nx
import osmnx as ox
from loguru import logger


class OSMRoutePlanResult(TypedDict):
    city: str
    transport: str
    node_ids: list[int]
    path_coords: list[list[float]]
    total_distance_m: float
    segment_count: int
    segment_distances_m: list[float]
    estimated_duration_s: float


class OSMService:
    """OSM 路网服务：按城市缓存路网并提供最短路径规划。"""

    _PLACE_ALIASES = {
        "北京": ("Beijing, China", "北京市, China", "北京, China"),
        "上海": ("Shanghai, China", "上海市, China", "上海, China"),
        "西安": ("Xi'an, Shaanxi, China", "西安市, China", "西安, China"),
        "杭州": ("Hangzhou, Zhejiang, China", "杭州市, China", "杭州, China"),
        "厦门": ("Xiamen, Fujian, China", "厦门市, China", "厦门, China"),
    }

    def _to_network_type(self, transport: str) -> str:
        if transport == "walk":
            return "walk"
        if transport == "bike":
            return "bike"
        raise ValueError("transport 仅支持 'walk' 或 'bike'")

    def _place_candidates(self, city_name: str) -> tuple[str, ...]:
        city = city_name.strip()
        if not city:
            raise ValueError("城市名称不能为空，无法加载 OSM 路网")
        if city in self._PLACE_ALIASES:
            return self._PLACE_ALIASES[city]
        return (f"{city}, China",)

    @lru_cache(maxsize=32)
    def get_city_graph(self, city_name: str, transport: str = "walk") -> nx.MultiDiGraph:
        network_type = self._to_network_type(transport)
        candidates = self._place_candidates(city_name)
        last_error: Exception | None = None

        for place in candidates:
            logger.info("开始加载 OSM 路网: city={} place={} network_type={}", city_name, place, network_type)
            try:
                graph = ox.graph_from_place(place, network_type=network_type, simplify=True)
            except Exception as exc:
                last_error = exc
                logger.warning("OSM 路网加载失败，将尝试下一个候选: place={} error={}", place, exc)
                continue
            if graph.number_of_nodes() == 0:
                last_error = ValueError(f"城市路网为空: place={place}")
                logger.warning("OSM 路网为空，将尝试下一个候选: place={}", place)
                continue
            logger.info(
                "OSM 路网加载成功: city={} place={} transport={} nodes={} edges={}",
                city_name,
                place,
                transport,
                graph.number_of_nodes(),
                graph.number_of_edges(),
            )
            return graph

        tried_places = ", ".join(candidates)
        raise ValueError(
            f"加载城市路网失败: city={city_name}, transport={transport}, "
            f"tried_places=[{tried_places}], last_error={last_error}"
        ) from last_error

    def _nearest_node(self, graph: nx.MultiDiGraph, lng: float, lat: float, label: str = "point") -> int:
        try:
            node_id = ox.distance.nearest_nodes(graph, X=lng, Y=lat)
            node_id = int(node_id)
            logger.info("OSM 最近节点定位成功: label={} lat={} lng={} node_id={}", label, lat, lng, node_id)
            return node_id
        except Exception as exc:
            logger.warning(
                "ox.nearest_nodes 失败，回退到手动搜索: label={} lat={} lng={} error={}",
                label,
                lat,
                lng,
                exc,
            )

        best_node: int | None = None
        best_dist: float | None = None
        for node_id, data in graph.nodes(data=True):
            x = data.get("x")
            y = data.get("y")
            if x is None or y is None:
                continue
            dist = (float(x) - lng) ** 2 + (float(y) - lat) ** 2
            if best_dist is None or dist < best_dist:
                best_dist = dist
                best_node = int(node_id)

        if best_node is None:
            raise ValueError(f"无法定位最近路网节点: label={label}, lat={lat}, lng={lng}")
        logger.info(
            "OSM 最近节点手动定位成功: label={} lat={} lng={} node_id={} squared_dist={}",
            label,
            lat,
            lng,
            best_node,
            round(best_dist or 0.0, 12),
        )
        return best_node

    def _estimate_duration_seconds(self, total_distance_m: float, transport: str) -> float:
        self._to_network_type(transport)
        speed_mps = 1.4 if transport == "walk" else 4.0
        if total_distance_m <= 0:
            return 0.0
        return total_distance_m / speed_mps

    def route_planning(
        self,
        city: str,
        start_lat: float,
        start_lng: float,
        end_lat: float,
        end_lng: float,
        transport: str = "walk",
    ) -> OSMRoutePlanResult:
        started_at = perf_counter()
        self._to_network_type(transport)
        logger.info(
            "开始 OSM 路径规划: city={} transport={} start=({}, {}) end=({}, {})",
            city,
            transport,
            start_lat,
            start_lng,
            end_lat,
            end_lng,
        )

        graph = self.get_city_graph(city, transport)
        start_node = self._nearest_node(graph, start_lng, start_lat, label="start")
        end_node = self._nearest_node(graph, end_lng, end_lat, label="end")
        logger.info(
            "OSM 起终点最近节点: city={} transport={} start_node={} end_node={}",
            city,
            transport,
            start_node,
            end_node,
        )

        try:
            node_ids = nx.shortest_path(graph, start_node, end_node, weight="length")
        except nx.NetworkXNoPath as exc:
            raise ValueError(
                f"起点与终点之间无可达路径: city={city}, transport={transport}, "
                f"start_node={start_node}, end_node={end_node}"
            ) from exc
        except nx.NodeNotFound as exc:
            raise ValueError(
                f"无法在路网中定位起点或终点: city={city}, transport={transport}, "
                f"start_node={start_node}, end_node={end_node}"
            ) from exc

        total_distance_m = 0.0
        segment_distances_m: list[float] = []
        for u, v in zip(node_ids[:-1], node_ids[1:]):
            segment_length = 0.0
            edge_bundle = graph.get_edge_data(u, v)
            if edge_bundle:
                segment_length = min(float(edge.get("length", 0.0)) for edge in edge_bundle.values())
            segment_distances_m.append(round(segment_length, 2))
            total_distance_m += segment_length

        path_coords: list[list[float]] = []
        for node_id in node_ids:
            node_data = graph.nodes[node_id]
            lng = node_data.get("x")
            lat = node_data.get("y")
            if lng is None or lat is None:
                raise ValueError(f"路径节点缺少经纬度坐标: node_id={node_id}")
            path_coords.append([float(lat), float(lng)])

        total_distance_m_rounded = round(total_distance_m, 2)
        estimated_duration_s = round(
            self._estimate_duration_seconds(total_distance_m, transport), 2
        )
        elapsed_ms = (perf_counter() - started_at) * 1000
        logger.info(
            "OSM 路径规划完成: city={} transport={} nodes={} distance={}m eta={}s elapsed_ms={:.2f}",
            city,
            transport,
            len(node_ids),
            total_distance_m_rounded,
            estimated_duration_s,
            elapsed_ms,
        )
        return {
            "city": city,
            "transport": transport,
            "node_ids": [int(nid) for nid in node_ids],
            "path_coords": path_coords,
            "total_distance_m": total_distance_m_rounded,
            "segment_count": len(segment_distances_m),
            "segment_distances_m": segment_distances_m,
            "estimated_duration_s": estimated_duration_s,
        }
