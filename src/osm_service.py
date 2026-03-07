from __future__ import annotations

from functools import lru_cache
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

    def _to_network_type(self, transport: str) -> str:
        if transport == "walk":
            return "walk"
        if transport == "bike":
            return "bike"
        raise ValueError("transport 仅支持 'walk' 或 'bike'")

    @lru_cache(maxsize=32)
    def get_city_graph(self, city_name: str, transport: str = "walk") -> nx.MultiDiGraph:
        network_type = self._to_network_type(transport)
        place = f"{city_name}, China"
        logger.info(f"开始加载 OSM 路网: place={place}, network_type={network_type}")
        try:
            graph = ox.graph_from_place(place, network_type=network_type, simplify=True)
        except Exception as exc:
            raise ValueError(f"加载城市路网失败: {city_name}, {exc}") from exc
        if graph.number_of_nodes() == 0:
            raise ValueError(f"城市路网为空: {city_name}")
        return graph

    def _nearest_node(self, graph: nx.MultiDiGraph, lng: float, lat: float) -> int:
        try:
            node_id = ox.distance.nearest_nodes(graph, X=lng, Y=lat)
            return int(node_id)
        except Exception as exc:
            logger.warning(f"ox.nearest_nodes 失败，回退到手动搜索: {exc}")

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
            raise ValueError("路网节点缺少坐标，无法定位最近节点")
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
        graph = self.get_city_graph(city, transport)
        start_node = self._nearest_node(graph, start_lng, start_lat)
        end_node = self._nearest_node(graph, end_lng, end_lat)

        try:
            node_ids = nx.shortest_path(graph, start_node, end_node, weight="length")
        except nx.NetworkXNoPath as exc:
            raise ValueError("起点与终点之间无可达路径") from exc
        except nx.NodeNotFound as exc:
            raise ValueError("无法在路网中定位起点或终点") from exc

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
                raise ValueError("路径节点缺少经纬度坐标")
            path_coords.append([float(lat), float(lng)])

        total_distance_m_rounded = round(total_distance_m, 2)
        return {
            "city": city,
            "transport": transport,
            "node_ids": [int(nid) for nid in node_ids],
            "path_coords": path_coords,
            "total_distance_m": total_distance_m_rounded,
            "segment_count": len(segment_distances_m),
            "segment_distances_m": segment_distances_m,
            "estimated_duration_s": round(
                self._estimate_duration_seconds(total_distance_m, transport), 2
            ),
        }
