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

TEST_DB_PATH = os.path.join(PROJECT_ROOT, "tests", "tmp_search_scope.db")
if os.path.exists(TEST_DB_PATH):
    os.remove(TEST_DB_PATH)
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH.replace('\\', '/')}"

import api
from database import engine
from models import NationalSpot


def seed_national_spot() -> int:
    now = datetime.now()
    with Session(engine) as session:
        spot = NationalSpot(
            name="测试故宫景点",
            type="历史遗迹",
            latitude=39.916345,
            longitude=116.397155,
            description="测试搜索范围",
            city="北京",
            rating=4.9,
            created_at=now,
            updated_at=now,
        )
        session.add(spot)
        session.commit()
        session.refresh(spot)
        return spot.id


def main():
    with TestClient(api.app) as client:
        seed_id = seed_national_spot()

        national_resp = client.get(
            "/spots/search",
            params={"query": "故宫", "scope": "national", "limit": 5},
        )
        assert national_resp.status_code == 200
        national_data = national_resp.json()
        assert len(national_data) >= 1
        assert national_data[0]["scope"] == "national"
        assert national_data[0]["id"] == seed_id
        assert national_data[0]["city"] == "北京"

        campus_resp = client.get(
            "/spots/search",
            params={"query": "学一", "scope": "campus", "limit": 5},
        )
        assert campus_resp.status_code == 200
        campus_data = campus_resp.json()
        assert len(campus_data) >= 1
        assert campus_data[0]["scope"] == "campus"
        assert "x" in campus_data[0]
        assert "y" in campus_data[0]

    print("✅ 景点搜索 scope 测试通过")


if __name__ == "__main__":
    main()
