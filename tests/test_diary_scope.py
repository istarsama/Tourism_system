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

TEST_DB_PATH = os.path.join(PROJECT_ROOT, "tests", "tmp_diary_scope.db")
if os.path.exists(TEST_DB_PATH):
    os.remove(TEST_DB_PATH)
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH.replace('\\', '/')}"

import api
import diary
from database import engine
from models import NationalSpot, User


def seed_data() -> tuple[int, int]:
    now = datetime.now()
    with Session(engine) as session:
        user = User(username="scope_tester", password_hash="fake_hash", created_at=now)
        national_spot = NationalSpot(
            name="测试国家景点",
            type="人文景观",
            latitude=39.916345,
            longitude=116.397155,
            description="测试全国日记",
            city="北京",
            rating=4.8,
            created_at=now,
            updated_at=now,
        )
        session.add(user)
        session.add(national_spot)
        session.commit()
        session.refresh(user)
        session.refresh(national_spot)
        return user.id, national_spot.id


def main():
    with TestClient(api.app) as client:
        user_id, national_spot_id = seed_data()

        def fake_current_user():
            return User(id=user_id, username="scope_tester", password_hash="fake_hash")

        api.app.dependency_overrides[diary.get_current_user] = fake_current_user
        try:
            campus_create_resp = client.post(
                "/diaries/",
                json={
                    "scope": "campus",
                    "spot_id": 44,
                    "title": "校园日记测试",
                    "content": "校园范围日记内容",
                    "media_files": [],
                },
            )
            assert campus_create_resp.status_code == 200
            campus_diary = campus_create_resp.json()
            assert campus_diary["scope"] == "campus"
            assert campus_diary["spot_id"] == 44
            assert campus_diary["national_spot_id"] is None

            national_create_resp = client.post(
                "/diaries/",
                json={
                    "scope": "national",
                    "national_spot_id": national_spot_id,
                    "title": "全国日记测试",
                    "content": "全国范围日记内容",
                    "media_files": [],
                },
            )
            assert national_create_resp.status_code == 200
            national_diary = national_create_resp.json()
            assert national_diary["scope"] == "national"
            assert national_diary["spot_id"] is None
            assert national_diary["national_spot_id"] == national_spot_id

            list_campus_resp = client.get("/diaries/spot/44", params={"scope": "campus"})
            assert list_campus_resp.status_code == 200
            campus_list = list_campus_resp.json()
            assert len(campus_list) >= 1
            assert campus_list[0]["scope"] == "campus"

            list_national_resp = client.get(
                f"/diaries/spot/{national_spot_id}",
                params={"scope": "national"},
            )
            assert list_national_resp.status_code == 200
            national_list = list_national_resp.json()
            assert len(national_list) >= 1
            assert national_list[0]["scope"] == "national"

            search_national_resp = client.get("/diaries/search", params={"scope": "national"})
            assert search_national_resp.status_code == 200
            search_national_list = search_national_resp.json()
            assert len(search_national_list) >= 1
            assert all(d["scope"] == "national" for d in search_national_list)
        finally:
            api.app.dependency_overrides.pop(diary.get_current_user, None)

    print("✅ 日记 scope 适配测试通过")


if __name__ == "__main__":
    main()
