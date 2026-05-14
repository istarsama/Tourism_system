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


def test_route_planning_uses_lat_lng_order_and_distance():
    service = OSMService()
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


def test_bike_duration_uses_bike_speed_without_transport_fallback():
    service = OSMService()
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


def test_invalid_transport_is_rejected():
    service = OSMService()

    with pytest.raises(ValueError, match="walk.*bike"):
        service.route_planning(
            city="北京",
            start_lat=39.916345,
            start_lng=116.397155,
            end_lat=39.999912,
            end_lng=116.275522,
            transport="bus",
        )


def test_no_path_returns_clear_value_error():
    service = OSMService()
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


def test_missing_path_coordinate_returns_node_id():
    service = OSMService()
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


def test_get_city_graph_tries_beijing_alias_before_chinese_place(monkeypatch):
    service = OSMService()
    service.get_city_graph.cache_clear()
    graph = _build_route_graph()
    calls = []

    def fake_graph_from_place(place, network_type, simplify):
        calls.append((place, network_type, simplify))
        if place != "Beijing, China":
            raise RuntimeError("bad place")
        return graph

    monkeypatch.setattr(osm_service.ox, "graph_from_place", fake_graph_from_place)

    result = service.get_city_graph("北京", "walk")

    assert result is graph
    assert calls == [("Beijing, China", "walk", True)]
