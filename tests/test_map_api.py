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
from models import NationalSpot, NationalSpotXHSNote


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
            existing = NationalSpot(
                name="测试景点-故宫",
                type="历史遗迹",
                latitude=39.916345,
                longitude=116.397155,
                description="测试数据",
                city="北京",
                province="北京",
                flower_type="海棠",
                best_season="4月",
                xhs_query="北京 故宫 海棠",
                xhs_fetch_status="success",
                xhs_fetch_message="已同步 1 条小红书帖子预览。",
                xhs_cookie_needs_refresh=False,
                xhs_note_count=1,
                xhs_last_fetched_at=now,
                rating=4.9,
                created_at=now,
                updated_at=now,
            )
            session.add(existing)
            session.commit()
            session.refresh(existing)
            session.add(
                NationalSpotXHSNote(
                    national_spot_id=existing.id,
                    xhs_note_id="xhs-map-api-1",
                    title="故宫海棠拍照攻略",
                    content_preview="春天在故宫看海棠真的很出片。",
                    thumbnail_url="https://example.com/thumbnail.jpg",
                    xhs_url="https://www.xiaohongshu.com/explore/xhs-map-api-1",
                    author_name="测试作者",
                    author_id="author_1",
                    liked_count=128,
                    image_urls_json='["https://example.com/thumbnail.jpg"]',
                    rank_order=0,
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
        assert mode_campus.json()["supports_slippy_map"] is False
        assert mode_campus.json()["coordinate_system"] == "campus_pixel"
        assert mode_campus.json()["tile_layer"] is None

        mode_national = client.get("/map/mode", params={"scope": "national"})
        assert mode_national.status_code == 200
        assert mode_national.json()["data_source"] == "national_spot"
        assert mode_national.json()["supports_slippy_map"] is True
        assert mode_national.json()["coordinate_system"] == "wgs84"
        assert mode_national.json()["tile_layer"]["tile_url"] == "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        assert mode_national.json()["tile_layer"]["usage_tier"] == "demo"

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
        assert data[0]["xhs_note_count"] == 1
        assert data[0]["xhs_fetch_status"] == "success"
        assert data[0]["xhs_cookie_needs_refresh"] is False
        assert data[0]["xhs_notes_preview"][0]["thumbnail_url"] == "https://example.com/thumbnail.jpg"
        assert data[0]["xhs_notes_preview"][0]["xhs_url"].startswith("https://www.xiaohongshu.com/explore/")

    print("✅ 地图模式 API 测试通过")


if __name__ == "__main__":
    main()
