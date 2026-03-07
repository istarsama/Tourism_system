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

TEST_DB_PATH = os.path.join(PROJECT_ROOT, "tests", "tmp_map_api.db")
if os.path.exists(TEST_DB_PATH):
    os.remove(TEST_DB_PATH)
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH.replace('\\', '/')}"

import api
from database import engine
from models import NationalSpot


def seed_national_spots() -> None:
    now = datetime.now()
    with Session(engine) as session:
        existing = session.exec(
            select(NationalSpot).where(
                NationalSpot.name == "测试景点-故宫",
                NationalSpot.city == "北京",
            )
        ).first()
        if not existing:
            session.add(
                NationalSpot(
                    name="测试景点-故宫",
                    type="历史遗迹",
                    latitude=39.916345,
                    longitude=116.397155,
                    description="测试数据",
                    city="北京",
                    rating=4.9,
                    created_at=now,
                    updated_at=now,
                )
            )
        session.commit()


def main():
    with TestClient(api.app) as client:
        mode_campus = client.get("/map/mode", params={"scope": "campus"})
        assert mode_campus.status_code == 200
        assert mode_campus.json()["scope"] == "campus"

        mode_national = client.get("/map/mode", params={"scope": "national"})
        assert mode_national.status_code == 200
        assert mode_national.json()["data_source"] == "national_spot"

        graph_data = client.get("/map/campus-graph")
        assert graph_data.status_code == 200
        assert "nodes" in graph_data.json()
        assert "edges" in graph_data.json()

        seed_national_spots()
        spots = client.get(
            "/map/national-spots",
            params={"city": "北京", "type": "历史遗迹"},
        )
        assert spots.status_code == 200
        data = spots.json()
        assert len(data) >= 1
        assert data[0]["city"] == "北京"
        assert "diary_count" in data[0]
        assert "diary_api" in data[0]

    print("✅ 地图模式 API 测试通过")


if __name__ == "__main__":
    main()
