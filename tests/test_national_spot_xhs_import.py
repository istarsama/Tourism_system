import os
import sys

from fastapi.testclient import TestClient
from sqlmodel import Session, select

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(CURRENT_DIR, "..")
SRC_PATH = os.path.join(PROJECT_ROOT, "src")

if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

TEST_DB_PATH = os.path.join(PROJECT_ROOT, "tests", "tmp_national_spot_xhs_import.db")
if os.path.exists(TEST_DB_PATH):
    os.remove(TEST_DB_PATH)
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH.replace('\\', '/')}"

import api
from database import engine, init_db
from models import NationalSpot, NationalSpotXHSNote
from national_spot_importer import import_national_spots
from national_spot_xhs import COOKIE_REFRESH_HINT, XHSFetchResult


def fake_fetcher(query: str, limit: int) -> XHSFetchResult:
    if "武汉大学" in query:
        return XHSFetchResult(
            status="cookie_expired",
            notes=[],
            message=f"❌ Cookie 失效: 401\n{COOKIE_REFRESH_HINT}",
            cookie_needs_refresh=True,
        )

    return XHSFetchResult(
        status="success",
        notes=[
            {
                "note_id": "xhs-import-1",
                "title": "玉渊潭赏樱攻略",
                "content_preview": "适合测试导入脚本是否把预览和链接写进数据库。",
                "thumbnail_url": "https://example.com/import-preview.jpg",
                "xhs_url": "https://www.xiaohongshu.com/explore/xhs-import-1",
                "author_name": "导入测试作者",
                "author_id": "import_author",
                "likes": 321,
                "images": ["https://example.com/import-preview.jpg"],
            }
        ],
        message="已同步 1 条小红书帖子预览。",
        cookie_needs_refresh=False,
    )


def main():
    init_db()
    dataset = [
        {
            "name": "玉渊潭公园",
            "type": "城市公园",
            "latitude": 39.922539,
            "longitude": 116.320764,
            "description": "测试导入成功链路",
            "city": "北京",
            "province": "北京",
            "flower_type": "樱花",
            "best_season": "4月",
            "search_keywords": ["玉渊潭樱花", "北京赏樱"],
            "xhs_query": "北京 玉渊潭公园 樱花",
        },
        {
            "name": "武汉大学樱花大道",
            "type": "校园景观",
            "latitude": 30.536228,
            "longitude": 114.364194,
            "description": "测试 Cookie 失效链路",
            "city": "武汉",
            "province": "湖北",
            "flower_type": "樱花",
            "best_season": "3月",
            "search_keywords": ["武汉大学樱花"],
            "xhs_query": "武汉大学 樱花",
        },
    ]

    with Session(engine) as session:
        stats = import_national_spots(
            session,
            dataset,
            fetch_xhs=True,
            note_limit=3,
            fetcher=fake_fetcher,
        )

        assert stats["created"] == 2
        assert stats["updated"] == 0
        assert stats["xhs_success"] == 1
        assert stats["xhs_cookie_expired"] == 1
        assert stats["xhs_failed"] == 0

        success_spot = session.exec(select(NationalSpot).where(NationalSpot.name == "玉渊潭公园")).first()
        cookie_spot = session.exec(select(NationalSpot).where(NationalSpot.name == "武汉大学樱花大道")).first()

        assert success_spot is not None
        assert success_spot.xhs_fetch_status == "success"
        assert success_spot.xhs_note_count == 1

        note_rows = session.exec(
            select(NationalSpotXHSNote).where(NationalSpotXHSNote.national_spot_id == success_spot.id)
        ).all()
        assert len(note_rows) == 1
        assert note_rows[0].xhs_url == "https://www.xiaohongshu.com/explore/xhs-import-1"

        assert cookie_spot is not None
        assert cookie_spot.xhs_fetch_status == "cookie_expired"
        assert cookie_spot.xhs_cookie_needs_refresh is True
        assert COOKIE_REFRESH_HINT in (cookie_spot.xhs_fetch_message or "")

    # 再执行一次，验证幂等更新而不是重复插入。
    dataset[0]["description"] = "测试重复执行时会更新而不是重复创建"
    with Session(engine) as session:
        stats = import_national_spots(
            session,
            dataset,
            fetch_xhs=True,
            note_limit=3,
            fetcher=fake_fetcher,
        )
        assert stats["created"] == 0
        assert stats["updated"] == 2

        success_spot = session.exec(select(NationalSpot).where(NationalSpot.name == "玉渊潭公园")).first()
        assert success_spot is not None
        assert success_spot.description == "测试重复执行时会更新而不是重复创建"
        note_rows = session.exec(
            select(NationalSpotXHSNote).where(NationalSpotXHSNote.national_spot_id == success_spot.id)
        ).all()
        assert len(note_rows) == 1

    with TestClient(api.app) as client:
        cookie_resp = client.get("/map/national-spots", params={"city": "武汉", "limit": 20})
        assert cookie_resp.status_code == 200
        cookie_data = cookie_resp.json()
        assert len(cookie_data) == 1
        assert cookie_data[0]["xhs_fetch_status"] == "cookie_expired"
        assert cookie_data[0]["xhs_cookie_needs_refresh"] is True
        assert COOKIE_REFRESH_HINT in cookie_data[0]["xhs_fetch_message"]
        assert cookie_data[0]["xhs_notes_preview"] == []

    print("✅ 全国赏花景点导入与小红书预览测试通过")


if __name__ == "__main__":
    main()
