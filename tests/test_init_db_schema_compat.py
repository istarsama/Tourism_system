import os
import sys

from sqlalchemy import inspect, text
from sqlmodel import Session, create_engine, select

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(CURRENT_DIR, "..")
SRC_PATH = os.path.join(PROJECT_ROOT, "src")

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

TEST_DB_PATH = os.path.join(PROJECT_ROOT, "tests", "tmp_init_db_schema_compat.db")
if os.path.exists(TEST_DB_PATH):
    os.remove(TEST_DB_PATH)
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH.replace('\\', '/')}"

from database import engine, init_db
from models import NationalSpot
from tools.import_national_flower_spots import import_national_flower_spots


def create_legacy_national_spot_table() -> None:
    """
    手工创建一个缺少赏花扩展字段的旧版 national_spot 表。

    这个场景正是用户线上报错的根因：表已经存在，但结构停留在旧版本，
    导致 ORM 查询新列时直接失败。
    """

    legacy_engine = create_engine(os.environ["DATABASE_URL"])
    with legacy_engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE national_spot (
                    id INTEGER PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    type VARCHAR(100) NOT NULL,
                    latitude FLOAT NOT NULL,
                    longitude FLOAT NOT NULL,
                    description TEXT,
                    city VARCHAR(100) NOT NULL,
                    rating FLOAT NOT NULL DEFAULT 4.5,
                    is_active BOOLEAN NOT NULL DEFAULT 1,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP
                )
                """
            )
        )


def main() -> None:
    create_legacy_national_spot_table()

    # init_db() 需要先补齐旧表缺列，然后导入脚本才能安全执行 select(NationalSpot)。
    init_db()

    columns = {
        column["name"]
        for column in inspect(engine).get_columns("national_spot")
    }
    assert "province" in columns
    assert "xhs_fetch_status" in columns
    assert "xhs_cookie_needs_refresh" in columns

    stats = import_national_flower_spots(
        os.path.join(PROJECT_ROOT, "data", "national_flower_spots.json"),
        skip_fetch=True,
    )
    assert stats["created"] > 0
    assert stats["updated"] == 0

    with Session(engine) as session:
        spot = session.exec(
            select(NationalSpot).where(NationalSpot.province.is_not(None))
        ).first()
        assert spot is not None
        assert spot.xhs_fetch_status == "pending"
        assert spot.xhs_cookie_needs_refresh is False

    print("✅ init_db 兼容升级可补齐旧版 national_spot 表结构")


if __name__ == "__main__":
    main()
