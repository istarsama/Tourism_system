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

TEST_DB_PATH = os.path.join(PROJECT_ROOT, "tests", "tmp_osm_frontend_contract.db")
if os.path.exists(TEST_DB_PATH):
    os.remove(TEST_DB_PATH)
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH.replace('\\', '/')}"

import api
import diary
from database import engine
from models import NationalSpot, NationalSpotXHSNote, User


def seed_user_and_spots() -> tuple[int, int, int]:
    now = datetime.now()
    with Session(engine) as session:
        user = User(username="frontend_osm_tester", password_hash="fake_hash", created_at=now)
        start_spot = NationalSpot(
            name="前端联调故宫",
            type="历史遗迹",
            latitude=39.916345,
            longitude=116.397155,
            description="前端联调起点",
            city="北京",
            rating=4.9,
            created_at=now,
            updated_at=now,
        )
        end_spot = NationalSpot(
            name="前端联调颐和园",
            type="历史遗迹",
            latitude=39.999912,
            longitude=116.275522,
            description="前端联调终点",
            city="北京",
            rating=4.8,
            created_at=now,
            updated_at=now,
        )
        session.add(user)
        session.add(start_spot)
        session.add(end_spot)
        session.commit()
        session.refresh(user)
        session.refresh(start_spot)
        session.refresh(end_spot)
        session.add(
            NationalSpotXHSNote(
                national_spot_id=start_spot.id,
                xhs_note_id="xhs-osm-1",
                title="前端联调故宫赏花预览",
                content_preview="这里用于验证 OSM 模式能拿到帖子预览。",
                thumbnail_url="https://example.com/osm-preview.jpg",
                xhs_url="https://www.xiaohongshu.com/explore/xhs-osm-1",
                author_name="联调作者",
                author_id="osm_author",
                liked_count=256,
                image_urls_json='["https://example.com/osm-preview.jpg"]',
                rank_order=0,
                created_at=now,
                updated_at=now,
            )
        )
        start_spot.xhs_query = "北京 故宫 赏花"
        start_spot.xhs_fetch_status = "success"
        start_spot.xhs_fetch_message = "已同步 1 条小红书帖子预览。"
        start_spot.xhs_note_count = 1
        start_spot.xhs_last_fetched_at = now
        session.add(start_spot)
        session.commit()
        return user.id, start_spot.id, end_spot.id


def main():
    with TestClient(api.app) as client:
        user_id, start_spot_id, end_spot_id = seed_user_and_spots()

        def fake_current_user():
            return User(id=user_id, username="frontend_osm_tester", password_hash="fake_hash")

        def fake_route_planning(**kwargs):
            return {
                "city": kwargs["city"],
                "transport": kwargs["transport"],
                "node_ids": [101, 102, 103],
                "path_coords": [[39.916345, 116.397155], [39.95, 116.34], [39.999912, 116.275522]],
                "total_distance_m": 12800.5,
                "segment_count": 2,
                "segment_distances_m": [5200.25, 7600.25],
                "estimated_duration_s": 9143.21,
            }

        api.app.dependency_overrides[diary.get_current_user] = fake_current_user
        original_route_planning = api.osm_service.route_planning
        api.osm_service.route_planning = fake_route_planning

        try:
            mode_resp = client.get("/map/mode", params={"scope": "national"})
            assert mode_resp.status_code == 200
            mode_data = mode_resp.json()
            assert mode_data["scope"] == "national"
            assert mode_data["map_provider"] == "osm"
            assert mode_data["data_source"] == "national_spot"
            assert mode_data["supports_slippy_map"] is True
            assert mode_data["coordinate_system"] == "wgs84"
            assert mode_data["tile_layer"]["tile_url"] == "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            assert mode_data["tile_layer"]["attribution"] == "&copy; OpenStreetMap contributors"
            assert mode_data["tile_layer"]["requires_backend_proxy"] is False

            create_diary_resp = client.post(
                "/diaries/",
                json={
                    "scope": "national",
                    "national_spot_id": start_spot_id,
                    "title": "前端联调全国日记",
                    "content": "用于验证 OSM 地图与日记接口的联调链路",
                    "media_files": ["https://example.com/demo.jpg"],
                },
            )
            assert create_diary_resp.status_code == 200
            created_diary = create_diary_resp.json()
            assert created_diary["scope"] == "national"
            assert created_diary["national_spot_id"] == start_spot_id
            assert created_diary["media_files"] == ["https://example.com/demo.jpg"]

            spots_resp = client.get(
                "/map/national-spots",
                params={"city": "北京", "type": "历史遗迹", "limit": 20},
            )
            assert spots_resp.status_code == 200
            spots_data = spots_resp.json()
            start_spot = next((item for item in spots_data if item["id"] == start_spot_id), None)
            assert start_spot is not None
            assert start_spot["city"] == "北京"
            assert start_spot["diary_count"] >= 1
            assert start_spot["diary_api"] == f"/diaries/spot/{start_spot_id}?scope=national"
            assert start_spot["xhs_note_count"] == 1
            assert start_spot["xhs_fetch_status"] == "success"
            assert start_spot["xhs_notes_preview"][0]["thumbnail_url"] == "https://example.com/osm-preview.jpg"
            assert start_spot["xhs_notes_preview"][0]["xhs_url"] == "https://www.xiaohongshu.com/explore/xhs-osm-1"

            search_resp = client.get(
                "/spots/search",
                params={
                    "query": "故宫",
                    "scope": "national",
                    "city": "北京",
                    "limit": 5,
                },
            )
            assert search_resp.status_code == 200
            search_data = search_resp.json()
            assert len(search_data) >= 1
            assert search_data[0]["scope"] == "national"
            assert search_data[0]["id"] == start_spot_id
            assert "latitude" in search_data[0]
            assert "longitude" in search_data[0]
            assert search_data[0]["xhs_note_count"] == 1
            assert search_data[0]["xhs_fetch_status"] == "success"

            navigate_resp = client.post(
                "/navigate/osm",
                json={
                    "start_spot_id": start_spot_id,
                    "end_spot_id": end_spot_id,
                    "transport": "walk",
                },
            )
            assert navigate_resp.status_code == 200
            navigate_data = navigate_resp.json()
            assert navigate_data["city"] == "北京"
            assert navigate_data["transport"] == "walk"
            assert navigate_data["start_spot_id"] == start_spot_id
            assert navigate_data["end_spot_id"] == end_spot_id
            assert navigate_data["segment_count"] == 2
            assert navigate_data["segment_distances_m"] == [5200.25, 7600.25]
            assert navigate_data["estimated_duration_s"] == 9143.21
            assert navigate_data["path_coords"][0] == [39.916345, 116.397155]
            assert all(len(coord) == 2 for coord in navigate_data["path_coords"])
            assert all(20 <= coord[0] <= 55 for coord in navigate_data["path_coords"])
            assert all(70 <= coord[1] <= 140 for coord in navigate_data["path_coords"])

            diary_list_resp = client.get(start_spot["diary_api"])
            assert diary_list_resp.status_code == 200
            diary_list = diary_list_resp.json()
            assert len(diary_list) >= 1
            assert diary_list[0]["scope"] == "national"
            assert diary_list[0]["national_spot_id"] == start_spot_id
        finally:
            api.osm_service.route_planning = original_route_planning
            api.app.dependency_overrides.pop(diary.get_current_user, None)

    print("✅ OSM 前端对接链路测试通过")


if __name__ == "__main__":
    main()
