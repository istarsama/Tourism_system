import os
import sys
from pathlib import Path

from sqlmodel import Session, select

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
TOOLS_PATH = PROJECT_ROOT / "tools"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))
if str(TOOLS_PATH) not in sys.path:
    sys.path.insert(0, str(TOOLS_PATH))

TEST_DB_PATH = PROJECT_ROOT / "tests" / "tmp_osm_preload.db"
if TEST_DB_PATH.exists():
    TEST_DB_PATH.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH.as_posix()}"

from database import engine, init_db  # noqa: E402
from models import NationalSpot, RouteCache  # noqa: E402
from preload_osm_graphs import clear_route_cache, get_active_cities  # noqa: E402


def main():
    init_db()
    with Session(engine) as session:
        session.add(
            NationalSpot(
                name="预加载测试景点",
                type="历史遗迹",
                latitude=39.916345,
                longitude=116.397155,
                city="北京",
            )
        )
        session.add(
            RouteCache(
                cache_key="osm:v1:北京:walk:1:2",
                mode="osm",
                provider="osmnx",
            )
        )
        session.add(
            RouteCache(
                cache_key="osm:v1:北京:bike:1:2",
                mode="osm",
                provider="osmnx",
            )
        )
        session.commit()

        assert get_active_cities(session, None) == ["北京"]
        assert get_active_cities(session, "上海") == ["上海"]
        assert clear_route_cache(session, "北京", "walk") == 1

        remaining_keys = {
            cache.cache_key
            for cache in session.exec(select(RouteCache)).all()
        }
        assert remaining_keys == {"osm:v1:北京:bike:1:2"}

    print("✅ OSM 预加载工具城市筛选与强制刷新缓存清理测试通过")


if __name__ == "__main__":
    main()
