import os
import sys
from datetime import datetime

from fastapi.testclient import TestClient
from sqlmodel import Session, select

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(CURRENT_DIR, "..")
SRC_PATH = os.path.join(PROJECT_ROOT, "src")

if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

TEST_DB_PATH = os.path.join(PROJECT_ROOT, "tests", "tmp_osm_api.db")
if os.path.exists(TEST_DB_PATH):
    os.remove(TEST_DB_PATH)
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH.replace('\\', '/')}"

import api
from database import engine
from models import NationalSpot, RouteCache


def seed_national_spots() -> tuple[int, int, int, int]:
    now = datetime.now()
    with Session(engine) as session:
        start = NationalSpot(
            name="测试OSM起点",
            type="历史遗迹",
            latitude=39.916345,
            longitude=116.397155,
            description="测试起点",
            city="北京",
            rating=4.9,
            created_at=now,
            updated_at=now,
        )
        end = NationalSpot(
            name="测试OSM终点",
            type="历史遗迹",
            latitude=39.999912,
            longitude=116.275522,
            description="测试终点",
            city="北京",
            rating=4.8,
            created_at=now,
            updated_at=now,
        )
        via = NationalSpot(
            name="测试OSM途经点",
            type="城市公园",
            latitude=39.950000,
            longitude=116.340000,
            description="测试途经点",
            city="北京",
            rating=4.7,
            created_at=now,
            updated_at=now,
        )
        cross_city = NationalSpot(
            name="测试跨城终点",
            type="人文景观",
            latitude=31.240011,
            longitude=121.490317,
            description="测试跨城终点",
            city="上海",
            rating=4.7,
            created_at=now,
            updated_at=now,
        )
        session.add(start)
        session.add(via)
        session.add(end)
        session.add(cross_city)
        session.commit()
        session.refresh(start)
        session.refresh(via)
        session.refresh(end)
        session.refresh(cross_city)
        return start.id, via.id, end.id, cross_city.id


def main():
    with TestClient(api.app) as client:
        start_id, via_id, end_id, cross_city_id = seed_national_spots()

        original_route_planning = api.osm_service.route_planning
        route_calls = []

        def fake_route_planning(**kwargs):
            route_calls.append(kwargs)
            return {
                "city": kwargs["city"],
                "transport": kwargs["transport"],
                "node_ids": [101, 102, 103],
                "path_coords": [[39.91, 116.39], [39.95, 116.34], [40.00, 116.27]],
                "total_distance_m": 12800.5,
                "segment_count": 2,
                "segment_distances_m": [5200.25, 7600.25],
                "estimated_duration_s": 9143.21,
            }

        api.osm_service.route_planning = fake_route_planning
        try:
            ok_resp = client.post(
                "/navigate/osm",
                json={
                    "start_spot_id": start_id,
                    "end_spot_id": end_id,
                    "transport": "walk",
                },
            )
            assert ok_resp.status_code == 200
            ok_data = ok_resp.json()
            assert ok_data["start_spot_id"] == start_id
            assert ok_data["end_spot_id"] == end_id
            assert ok_data["city"] == "北京"
            assert ok_data["transport"] == "walk"
            assert ok_data["node_ids"] == [101, 102, 103]
            assert ok_data["path_coords"] == [[39.91, 116.39], [39.95, 116.34], [40.0, 116.27]]
            assert ok_data["path_coords"][0][0] == 39.91
            assert ok_data["path_coords"][0][1] == 116.39
            assert ok_data["total_distance_m"] == 12800.5
            assert ok_data["segment_count"] == 2
            assert ok_data["segment_distances_m"] == [5200.25, 7600.25]
            assert ok_data["estimated_duration_s"] == 9143.21
            assert len(route_calls) == 1

            cached_resp = client.post(
                "/navigate/osm",
                json={
                    "start_spot_id": start_id,
                    "end_spot_id": end_id,
                    "transport": "walk",
                },
            )
            assert cached_resp.status_code == 200
            assert cached_resp.json() == ok_data
            assert len(route_calls) == 1

            multi_resp = client.post(
                "/navigate/osm",
                json={
                    "start_spot_id": start_id,
                    "via_spot_ids": [via_id],
                    "end_spot_id": end_id,
                    "transport": "walk",
                },
            )
            assert multi_resp.status_code == 200
            multi_data = multi_resp.json()
            assert multi_data["via_spot_ids"] == [via_id]
            assert multi_data["total_distance_m"] == 25601.0
            assert len(multi_data["legs"]) == 2
            assert multi_data["legs"][0]["start_spot_id"] == start_id
            assert multi_data["legs"][0]["end_spot_id"] == via_id
            assert multi_data["legs"][1]["start_spot_id"] == via_id
            assert multi_data["legs"][1]["end_spot_id"] == end_id
            assert len(route_calls) == 3

            multi_cached_resp = client.post(
                "/navigate/osm",
                json={
                    "start_spot_id": start_id,
                    "via_spot_ids": [via_id],
                    "end_spot_id": end_id,
                    "transport": "walk",
                },
            )
            assert multi_cached_resp.status_code == 200
            assert multi_cached_resp.json() == multi_data
            assert len(route_calls) == 3

            reverse_resp = client.post(
                "/navigate/osm",
                json={
                    "start_spot_id": end_id,
                    "end_spot_id": start_id,
                    "transport": "walk",
                },
            )
            assert reverse_resp.status_code == 200
            assert len(route_calls) == 4

            bike_resp = client.post(
                "/navigate/osm",
                json={
                    "start_spot_id": start_id,
                    "end_spot_id": end_id,
                    "transport": "bike",
                },
            )
            assert bike_resp.status_code == 200
            assert len(route_calls) == 5

            with Session(engine) as session:
                route_caches = session.exec(select(RouteCache)).all()
                assert len(route_caches) == 4

            required_compat_fields = {
                "city",
                "transport",
                "start_spot_id",
                "end_spot_id",
                "via_spot_ids",
                "node_ids",
                "path_coords",
                "total_distance_m",
                "legs",
            }
            assert required_compat_fields.issubset(set(ok_data.keys()))

            invalid_transport_resp = client.post(
                "/navigate/osm",
                json={
                    "start_spot_id": start_id,
                    "end_spot_id": end_id,
                    "transport": "bus",
                },
            )
            assert invalid_transport_resp.status_code == 400
            assert "walk" in invalid_transport_resp.text
            assert "bike" in invalid_transport_resp.text

            cross_city_resp = client.post(
                "/navigate/osm",
                json={
                    "start_spot_id": start_id,
                    "end_spot_id": cross_city_id,
                    "transport": "walk",
                },
            )
            assert cross_city_resp.status_code == 400
            assert "起点城市=北京" in cross_city_resp.text
            assert "终点城市=上海" in cross_city_resp.text

            missing_start_resp = client.post(
                "/navigate/osm",
                json={
                    "start_spot_id": 999999,
                    "end_spot_id": end_id,
                    "transport": "walk",
                },
            )
            assert missing_start_resp.status_code == 404
            assert "起点全国景点不存在" in missing_start_resp.text

            missing_end_resp = client.post(
                "/navigate/osm",
                json={
                    "start_spot_id": start_id,
                    "end_spot_id": 999999,
                    "transport": "walk",
                },
            )
            assert missing_end_resp.status_code == 404
            assert "终点全国景点不存在" in missing_end_resp.text

            def failing_route_planning(**kwargs):
                raise ValueError("测试路网不可达")

            with Session(engine) as session:
                for route_cache in session.exec(select(RouteCache)).all():
                    session.delete(route_cache)
                session.commit()

            api.osm_service.route_planning = failing_route_planning
            failed_route_resp = client.post(
                "/navigate/osm",
                json={
                    "start_spot_id": start_id,
                    "end_spot_id": end_id,
                    "transport": "walk",
                },
            )
            assert failed_route_resp.status_code == 400
            assert "测试路网不可达" in failed_route_resp.text
        finally:
            api.osm_service.route_planning = original_route_planning

    print("✅ OSM 导航 API 测试通过")


if __name__ == "__main__":
    main()
