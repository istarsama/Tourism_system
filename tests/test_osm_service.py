import networkx as nx
import pytest

import osm_service
from osm_service import OSMService


def _build_route_graph() -> nx.MultiDiGraph:
    graph = nx.MultiDiGraph()
    graph.graph["crs"] = "epsg:4326"
    graph.add_node(1, x=116.397155, y=39.916345)
    graph.add_node(2, x=116.34, y=39.95)
    graph.add_node(3, x=116.275522, y=39.999912)
    graph.add_edge(1, 2, length=5200.25)
    graph.add_edge(1, 2, length=6000.0)
    graph.add_edge(2, 3, length=7600.25)
    return graph


def _make_service(tmp_path):
    return OSMService(cache_dir=tmp_path, metadata_writer=lambda **kwargs: None)


def _fake_save_graphml(graph, filepath):
    filepath.write_text("graphml", encoding="utf-8")


def test_route_planning_uses_lat_lng_order_and_distance(tmp_path):
    service = _make_service(tmp_path)
    graph = _build_route_graph()
    service.get_city_graph = lambda city, transport: graph
    service._nearest_node = lambda graph, lng, lat, label="point": 1 if label == "start" else 3

    result = service.route_planning(
        city="北京",
        start_lat=39.916345,
        start_lng=116.397155,
        end_lat=39.999912,
        end_lng=116.275522,
        transport="walk",
    )

    assert result["city"] == "北京"
    assert result["transport"] == "walk"
    assert result["node_ids"] == [1, 2, 3]
    assert result["path_coords"] == [
        [39.916345, 116.397155],
        [39.95, 116.34],
        [39.999912, 116.275522],
    ]
    assert result["total_distance_m"] == 12800.5
    assert result["segment_count"] == 2
    assert result["segment_distances_m"] == [5200.25, 7600.25]
    assert result["estimated_duration_s"] == round(12800.5 / 1.4, 2)


def test_bike_duration_uses_bike_speed_without_transport_fallback(tmp_path):
    service = _make_service(tmp_path)
    graph = _build_route_graph()
    service.get_city_graph = lambda city, transport: graph
    service._nearest_node = lambda graph, lng, lat, label="point": 1 if label == "start" else 3

    result = service.route_planning(
        city="北京",
        start_lat=39.916345,
        start_lng=116.397155,
        end_lat=39.999912,
        end_lng=116.275522,
        transport="bike",
    )

    assert result["transport"] == "bike"
    assert result["estimated_duration_s"] == round(12800.5 / 4.0, 2)


def test_invalid_transport_is_rejected(tmp_path):
    service = _make_service(tmp_path)

    with pytest.raises(ValueError, match="walk.*bike"):
        service.route_planning(
            city="北京",
            start_lat=39.916345,
            start_lng=116.397155,
            end_lat=39.999912,
            end_lng=116.275522,
            transport="bus",
        )


def test_no_path_returns_clear_value_error(tmp_path):
    service = _make_service(tmp_path)
    graph = nx.MultiDiGraph()
    graph.graph["crs"] = "epsg:4326"
    graph.add_node(1, x=116.397155, y=39.916345)
    graph.add_node(2, x=116.275522, y=39.999912)
    service.get_city_graph = lambda city, transport: graph
    service._nearest_node = lambda graph, lng, lat, label="point": 1 if label == "start" else 2

    with pytest.raises(ValueError, match="无可达路径"):
        service.route_planning(
            city="北京",
            start_lat=39.916345,
            start_lng=116.397155,
            end_lat=39.999912,
            end_lng=116.275522,
            transport="walk",
        )


def test_missing_path_coordinate_returns_node_id(tmp_path):
    service = _make_service(tmp_path)
    graph = nx.MultiDiGraph()
    graph.graph["crs"] = "epsg:4326"
    graph.add_node(1, x=116.397155, y=39.916345)
    graph.add_node(2, x=116.34)
    graph.add_edge(1, 2, length=100.0)
    service.get_city_graph = lambda city, transport: graph
    service._nearest_node = lambda graph, lng, lat, label="point": 1 if label == "start" else 2

    with pytest.raises(ValueError, match="node_id=2"):
        service.route_planning(
            city="北京",
            start_lat=39.916345,
            start_lng=116.397155,
            end_lat=39.95,
            end_lng=116.34,
            transport="walk",
        )


def test_get_city_graph_tries_beijing_alias_before_chinese_place(monkeypatch, tmp_path):
    service = _make_service(tmp_path)
    graph = _build_route_graph()
    calls = []

    def fake_graph_from_place(place, network_type, simplify):
        calls.append((place, network_type, simplify))
        if place != "Beijing, China":
            raise RuntimeError("bad place")
        return graph

    monkeypatch.setattr(osm_service.ox, "graph_from_place", fake_graph_from_place)
    monkeypatch.setattr(osm_service.ox, "save_graphml", _fake_save_graphml)

    result = service.get_city_graph("北京", "walk")

    assert result is graph
    assert calls == [("Beijing, China", "walk", True)]


def test_get_city_graph_loads_graphml_before_network(monkeypatch, tmp_path):
    metadata = []
    service = OSMService(cache_dir=tmp_path, metadata_writer=lambda **kwargs: metadata.append(kwargs))
    graph = _build_route_graph()
    cache_path = service.get_graph_cache_path("北京", "walk")
    cache_path.write_text("cached graph", encoding="utf-8")

    monkeypatch.setattr(osm_service.ox, "load_graphml", lambda filepath: graph)

    def fail_network(*args, **kwargs):
        raise AssertionError("file cache hit should not call graph_from_place")

    monkeypatch.setattr(osm_service.ox, "graph_from_place", fail_network)

    result = service.get_city_graph("北京", "walk")

    assert result is graph
    assert metadata[-1]["status"] == "ready"
    assert metadata[-1]["file_size_bytes"] > 0


def test_get_city_graph_downloads_and_saves_missing_graphml(monkeypatch, tmp_path):
    service = _make_service(tmp_path)
    graph = _build_route_graph()
    monkeypatch.setattr(osm_service.ox, "graph_from_place", lambda *args, **kwargs: graph)
    monkeypatch.setattr(osm_service.ox, "save_graphml", _fake_save_graphml)

    result = service.get_city_graph("北京", "walk")

    assert result is graph
    assert service.get_graph_cache_path("北京", "walk").read_text(encoding="utf-8") == "graphml"


def test_force_refresh_failure_preserves_existing_graphml(monkeypatch, tmp_path):
    service = _make_service(tmp_path)
    cache_path = service.get_graph_cache_path("北京", "walk")
    cache_path.write_text("existing graph", encoding="utf-8")

    def fail_network(*args, **kwargs):
        raise RuntimeError("offline")

    monkeypatch.setattr(osm_service.ox, "graph_from_place", fail_network)

    with pytest.raises(ValueError, match="加载城市路网失败"):
        service.get_city_graph("北京", "walk", force_refresh=True)

    assert cache_path.read_text(encoding="utf-8") == "existing graph"


def test_walk_and_bike_use_separate_graphml_files(tmp_path):
    service = _make_service(tmp_path)

    assert service.get_graph_cache_path("北京", "walk") != service.get_graph_cache_path("北京", "bike")


def test_force_refresh_replaces_memory_cache(monkeypatch, tmp_path):
    service = _make_service(tmp_path)
    first_graph = _build_route_graph()
    refreshed_graph = _build_route_graph()
    refreshed_graph.add_node(4, x=116.25, y=40.01)
    responses = [first_graph, refreshed_graph]

    def fake_graph_from_place(*args, **kwargs):
        return responses.pop(0)

    monkeypatch.setattr(osm_service.ox, "graph_from_place", fake_graph_from_place)
    monkeypatch.setattr(osm_service.ox, "save_graphml", _fake_save_graphml)

    initial = service.get_city_graph("北京", "walk")
    cached = service.get_city_graph("北京", "walk")
    refreshed = service.get_city_graph("北京", "walk", force_refresh=True)

    assert initial is first_graph
    assert cached is first_graph
    assert refreshed is refreshed_graph
