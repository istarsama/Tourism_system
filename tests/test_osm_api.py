import os
import sys
from datetime import datetime

from fastapi.testclient import TestClient
from sqlmodel import Session

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
from models import NationalSpot


def seed_national_spots() -> tuple[int, int, int]:
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
        session.add(end)
        session.add(cross_city)
        session.commit()
        session.refresh(start)
        session.refresh(end)
        session.refresh(cross_city)
        return start.id, end.id, cross_city.id


def main():
    with TestClient(api.app) as client:
        start_id, end_id, cross_city_id = seed_national_spots()

        original_route_planning = api.osm_service.route_planning

        def fake_route_planning(**kwargs):
            return {
                "city": kwargs["city"],
                "transport": kwargs["transport"],
                "node_ids": [101, 102, 103],
                "path_coords": [[39.91, 116.39], [39.95, 116.34], [40.00, 116.27]],
                "total_distance_m": 12800.5,
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
            assert ok_data["node_ids"] == [101, 102, 103]

            invalid_transport_resp = client.post(
                "/navigate/osm",
                json={
                    "start_spot_id": start_id,
                    "end_spot_id": end_id,
                    "transport": "bus",
                },
            )
            assert invalid_transport_resp.status_code == 400

            cross_city_resp = client.post(
                "/navigate/osm",
                json={
                    "start_spot_id": start_id,
                    "end_spot_id": cross_city_id,
                    "transport": "walk",
                },
            )
            assert cross_city_resp.status_code == 400
        finally:
            api.osm_service.route_planning = original_route_planning

    print("✅ OSM 导航 API 测试通过")


if __name__ == "__main__":
    main()
