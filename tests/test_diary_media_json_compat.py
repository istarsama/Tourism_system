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

TEST_DB_PATH = os.path.join(PROJECT_ROOT, "tests", "tmp_diary_media_compat.db")
if os.path.exists(TEST_DB_PATH):
    os.remove(TEST_DB_PATH)
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH.replace('\\', '/')}"

import api  # noqa: E402
from database import engine  # noqa: E402
from models import Diary, User  # noqa: E402


def seed_data():
    now = datetime.now()
    with Session(engine) as session:
        user = User(username="media_compat_user", password_hash="fake_hash", created_at=now)
        session.add(user)
        session.commit()
        session.refresh(user)

        # 历史脏数据：不是合法 JSON 字符串
        dirty_diary = Diary(
            user_id=user.id,
            spot_id=1,
            scope="campus",
            title="脏数据日记",
            content="media_json 不是合法 JSON",
            media_json="not-a-json-array",
            score=4.2,
            view_count=7,
            created_at=now,
        )
        session.add(dirty_diary)
        session.commit()


def main():
    with TestClient(api.app) as client:
        seed_data()
        resp = client.get("/diaries/spot/1", params={"scope": "campus", "sort_by": "heat"})
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert len(data) == 1
        assert data[0]["id"] > 0
        assert data[0]["media_files"] == []

    print("✅ 日记 media_json 兼容解析测试通过")


if __name__ == "__main__":
    main()
