import os
import sys
from datetime import datetime

from sqlalchemy import text
from sqlmodel import Session, create_engine, select

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(CURRENT_DIR, "..")
SRC_PATH = os.path.join(PROJECT_ROOT, "src")

if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

TEST_DB_PATH = os.path.join(PROJECT_ROOT, "tests", "tmp_national_spot_schema_upgrade.db")
if os.path.exists(TEST_DB_PATH):
    os.remove(TEST_DB_PATH)
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH.replace('\\', '/')}"

legacy_engine = create_engine(os.environ["DATABASE_URL"])
with legacy_engine.begin() as connection:
    connection.execute(
        text(
            """
            CREATE TABLE national_spot (
                id INTEGER PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                type VARCHAR(100) NOT NULL DEFAULT '综合景区',
                latitude FLOAT NOT NULL,
                longitude FLOAT NOT NULL,
                description TEXT,
                city VARCHAR(100) NOT NULL,
                rating FLOAT NOT NULL DEFAULT 4.5,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
            """
        )
    )
    connection.execute(
        text(
            """
            INSERT INTO national_spot (
                id, name, type, latitude, longitude, description, city, rating, is_active, created_at, updated_at
            ) VALUES (
                1, '玉渊潭公园', '城市公园', 39.922539, 116.320764, '旧版表结构中的景点记录', '北京', 4.5, 1, :created_at, :updated_at
            )
            """
        ),
        {"created_at": datetime.now(), "updated_at": datetime.now()},
    )

from database import engine, init_db
from models import NationalSpot
from national_spot_importer import import_national_spots


def main():
    init_db()

    dataset = [
        {
            "name": "玉渊潭公园",
            "type": "城市公园",
            "latitude": 39.922539,
            "longitude": 116.320764,
            "description": "升级后应能更新旧表记录",
            "city": "北京",
            "province": "北京",
            "flower_type": "樱花",
            "best_season": "4月",
            "search_keywords": ["玉渊潭樱花", "北京赏樱"],
            "xhs_query": "北京 玉渊潭公园 樱花",
            "source": "seed",
        }
    ]

    with Session(engine) as session:
        stats = import_national_spots(session, dataset, fetch_xhs=False)
        assert stats["created"] == 0
        assert stats["updated"] == 1

        spot = session.exec(
            select(NationalSpot).where(
                NationalSpot.name == "玉渊潭公园",
                NationalSpot.city == "北京",
            )
        ).first()
        assert spot is not None
        assert spot.province == "北京"
        assert spot.flower_type == "樱花"
        assert spot.best_season == "4月"
        assert spot.xhs_query == "北京 玉渊潭公园 樱花"
        assert spot.search_keywords_json == '["玉渊潭樱花", "北京赏樱"]'

    print("✅ national_spot 旧表结构兼容升级测试通过")


if __name__ == "__main__":
    main()
