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

TEST_DB_PATH = os.path.join(PROJECT_ROOT, "tests", "tmp_national_link.db")
if os.path.exists(TEST_DB_PATH):
    os.remove(TEST_DB_PATH)
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH.replace('\\', '/')}"

import api
from database import engine
from models import Diary, NationalSpot, User


def seed_data() -> int:
    now = datetime.now()
    with Session(engine) as session:
        user = User(username="map_link_user", password_hash="fake_hash", created_at=now)
        session.add(user)
        session.commit()
        session.refresh(user)

        spot = NationalSpot(
            name="地图联动测试景点",
            type="人文景观",
            latitude=39.91,
            longitude=116.39,
            description="地图联动测试",
            city="北京",
            rating=4.8,
            created_at=now,
            updated_at=now,
        )
        session.add(spot)
        session.commit()
        session.refresh(spot)

        session.add(
            Diary(
                user_id=user.id,
                scope="national",
                national_spot_id=spot.id,
                spot_id=None,
                title="联动日记",
                content="用于验证地图-日记闭环",
                media_json="[]",
                score=4.5,
                view_count=5,
                created_at=now,
            )
        )
        session.commit()
        return spot.id


def main():
    with TestClient(api.app) as client:
        spot_id = seed_data()
        resp = client.get(
            "/map/national-spots",
            params={"city": "北京", "type": "人文景观", "limit": 20},
        )
        assert resp.status_code == 200
        data = resp.json()
        target = next((item for item in data if item["id"] == spot_id), None)
        assert target is not None
        assert target["diary_count"] >= 1
        assert target["diary_api"] == f"/diaries/spot/{spot_id}?scope=national"

    print("✅ 全国景点与日记联动测试通过")


if __name__ == "__main__":
    main()
