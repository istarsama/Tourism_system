from __future__ import annotations

import hashlib
import os
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from threading import RLock
from time import perf_counter
from typing import Any, Callable, TypedDict

import networkx as nx
import osmnx as ox
from loguru import logger


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GRAPH_CACHE_DIR = PROJECT_ROOT / "data" / "osm_graphs"
DEFAULT_HTTP_CACHE_DIR = PROJECT_ROOT / "data" / "osmnx_cache"


class OSMRoutePlanResult(TypedDict):
    city: str
    transport: str
    node_ids: list[int]
    path_coords: list[list[float]]
    total_distance_m: float
    segment_count: int
    segment_distances_m: list[float]
    estimated_duration_s: float


def _persist_graph_cache_metadata(**metadata: Any) -> None:
    """Best-effort metadata persistence. Graph routing must not depend on the DB write."""
    try:
        from sqlmodel import Session, select

        from database import engine
        from models import OSMGraphCache

        with Session(engine) as session:
            cache = session.exec(
                select(OSMGraphCache).where(
                    OSMGraphCache.city == metadata["city"],
                    OSMGraphCache.transport == metadata["transport"],
                )
            ).first()
            if cache is None:
                cache = OSMGraphCache(
                    city=metadata["city"],
                    transport=metadata["transport"],
                    place_query=metadata["place_query"],
                    graph_path=metadata["graph_path"],
                )

            cache.place_query = metadata["place_query"]
            cache.graph_path = metadata["graph_path"]
            cache.node_count = metadata.get("node_count", 0)
            cache.edge_count = metadata.get("edge_count", 0)
            cache.file_size_bytes = metadata.get("file_size_bytes", 0)
            cache.status = metadata["status"]
            cache.last_error = metadata.get("last_error")
            if metadata.get("downloaded_at") is not None:
                cache.downloaded_at = metadata["downloaded_at"]
            cache.updated_at = datetime.now()
            session.add(cache)
            session.commit()
    except Exception as exc:
        logger.warning("OSM 路网缓存元数据写入失败，不影响导航: {}", exc)


class OSMService:
    """OSM 路网服务：内存 LRU -> GraphML 文件 -> OSMnx 联网下载。"""

    _PLACE_ALIASES = {
        "北京": ("Beijing, China", "北京市, China", "北京, China"),
        "上海": ("Shanghai, China", "上海市, China", "上海, China"),
        "西安": ("Xi'an, Shaanxi, China", "西安市, China", "西安, China"),
        "杭州": ("Hangzhou, Zhejiang, China", "杭州市, China", "杭州, China"),
        "厦门": ("Xiamen, Fujian, China", "厦门市, China", "厦门, China"),
    }

    def __init__(
        self,
        cache_dir: str | Path | None = None,
        metadata_writer: Callable[..., None] | None = None,
        max_memory_cache_size: int = 32,
    ) -> None:
        configured_cache_dir = cache_dir or os.getenv("OSM_GRAPH_CACHE_DIR")
        self.cache_dir = Path(configured_cache_dir or DEFAULT_GRAPH_CACHE_DIR)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._metadata_writer = metadata_writer or _persist_graph_cache_metadata
        self._memory_cache: OrderedDict[tuple[str, str], nx.MultiDiGraph] = OrderedDict()
        self._max_memory_cache_size = max_memory_cache_size
        self._graph_cache_lock = RLock()

        http_cache_dir = Path(os.getenv("OSMNX_HTTP_CACHE_DIR", str(DEFAULT_HTTP_CACHE_DIR)))
        http_cache_dir.mkdir(parents=True, exist_ok=True)
        ox.settings.use_cache = True
        ox.settings.cache_folder = str(http_cache_dir)

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

    def get_graph_cache_path(self, city_name: str, transport: str = "walk") -> Path:
        city = city_name.strip()
        self._to_network_type(transport)
        digest = hashlib.sha256(city.encode("utf-8")).hexdigest()[:16]
        return self.cache_dir / f"{digest}_{transport}.graphml"

    def get_graph_cache_info(self, city_name: str, transport: str = "walk") -> dict[str, Any]:
        path = self.get_graph_cache_path(city_name, transport)
        return {
            "city": city_name.strip(),
            "transport": transport,
            "graph_path": str(path),
            "exists": path.exists(),
            "file_size_bytes": path.stat().st_size if path.exists() else 0,
        }

    def clear_memory_cache(self, city_name: str | None = None, transport: str | None = None) -> None:
        with self._graph_cache_lock:
            if city_name is None and transport is None:
                self._memory_cache.clear()
                return

            city = city_name.strip() if city_name else None
            keys_to_remove = [
                key
                for key in self._memory_cache
                if (city is None or key[0] == city) and (transport is None or key[1] == transport)
            ]
            for key in keys_to_remove:
                self._memory_cache.pop(key, None)

    def _remember_graph(self, city_name: str, transport: str, graph: nx.MultiDiGraph) -> None:
        key = (city_name, transport)
        self._memory_cache.pop(key, None)
        self._memory_cache[key] = graph
        while len(self._memory_cache) > self._max_memory_cache_size:
            self._memory_cache.popitem(last=False)

    def _record_metadata(
        self,
        *,
        city: str,
        transport: str,
        place_query: str,
        graph_path: Path,
        status: str,
        graph: nx.MultiDiGraph | None = None,
        last_error: str | None = None,
        downloaded_at: datetime | None = None,
    ) -> None:
        try:
            self._metadata_writer(
                city=city,
                transport=transport,
                place_query=place_query,
                graph_path=str(graph_path),
                node_count=graph.number_of_nodes() if graph is not None else 0,
                edge_count=graph.number_of_edges() if graph is not None else 0,
                file_size_bytes=graph_path.stat().st_size if graph_path.exists() else 0,
                status=status,
                last_error=last_error,
                downloaded_at=downloaded_at,
            )
        except Exception as exc:
            logger.warning("OSM 路网缓存元数据回调失败，不影响导航: {}", exc)

    def _save_graph_atomically(self, graph: nx.MultiDiGraph, graph_path: Path) -> None:
        temp_path = graph_path.with_name(f"{graph_path.name}.tmp")
        try:
            temp_path.unlink(missing_ok=True)
            ox.save_graphml(graph, filepath=temp_path)
            os.replace(temp_path, graph_path)
        finally:
            temp_path.unlink(missing_ok=True)

    def get_city_graph(
        self,
        city_name: str,
        transport: str = "walk",
        *,
        force_refresh: bool = False,
    ) -> nx.MultiDiGraph:
        with self._graph_cache_lock:
            return self._get_city_graph_locked(city_name, transport, force_refresh=force_refresh)

    def _get_city_graph_locked(
        self,
        city_name: str,
        transport: str,
        *,
        force_refresh: bool,
    ) -> nx.MultiDiGraph:
        city = city_name.strip()
        network_type = self._to_network_type(transport)
        candidates = self._place_candidates(city)
        graph_path = self.get_graph_cache_path(city, transport)
        key = (city, transport)

        if force_refresh:
            self.clear_memory_cache(city, transport)
        elif key in self._memory_cache:
            graph = self._memory_cache.pop(key)
            self._memory_cache[key] = graph
            logger.info("命中 OSM 内存路网缓存: city={} transport={}", city, transport)
            return graph

        if graph_path.exists() and not force_refresh:
            try:
                started_at = perf_counter()
                graph = ox.load_graphml(filepath=graph_path)
                if graph.number_of_nodes() == 0:
                    raise ValueError("GraphML 路网为空")
                self._remember_graph(city, transport, graph)
                self._record_metadata(
                    city=city,
                    transport=transport,
                    place_query=candidates[0],
                    graph_path=graph_path,
                    graph=graph,
                    status="ready",
                )
                logger.info(
                    "命中 OSM GraphML 路网缓存: city={} transport={} nodes={} edges={} file_size={}B elapsed_ms={:.2f}",
                    city,
                    transport,
                    graph.number_of_nodes(),
                    graph.number_of_edges(),
                    graph_path.stat().st_size,
                    (perf_counter() - started_at) * 1000,
                )
                return graph
            except Exception as exc:
                logger.warning(
                    "OSM GraphML 缓存读取失败，将重新下载: city={} transport={} path={} error={}",
                    city,
                    transport,
                    graph_path,
                    exc,
                )

        last_error: Exception | None = None
        for place in candidates:
            logger.info("开始加载 OSM 路网: city={} place={} network_type={}", city, place, network_type)
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

            downloaded_at = datetime.now()
            try:
                self._save_graph_atomically(graph, graph_path)
                status = "ready"
                last_error_text = None
            except Exception as exc:
                status = "save_failed"
                last_error_text = str(exc)
                logger.warning(
                    "OSM 路网已下载但 GraphML 保存失败，本次仍可导航: city={} transport={} path={} error={}",
                    city,
                    transport,
                    graph_path,
                    exc,
                )

            self._remember_graph(city, transport, graph)
            self._record_metadata(
                city=city,
                transport=transport,
                place_query=place,
                graph_path=graph_path,
                graph=graph,
                status=status,
                last_error=last_error_text,
                downloaded_at=downloaded_at,
            )
            logger.info(
                "OSM 路网加载成功: city={} place={} transport={} nodes={} edges={} persisted={}",
                city,
                place,
                transport,
                graph.number_of_nodes(),
                graph.number_of_edges(),
                status == "ready",
            )
            return graph

        tried_places = ", ".join(candidates)
        error_text = (
            f"加载城市路网失败: city={city}, transport={transport}, "
            f"tried_places=[{tried_places}], last_error={last_error}"
        )
        self._record_metadata(
            city=city,
            transport=transport,
            place_query=candidates[0],
            graph_path=graph_path,
            status="refresh_failed" if graph_path.exists() else "failed",
            last_error=error_text,
        )
        raise ValueError(error_text) from last_error

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
