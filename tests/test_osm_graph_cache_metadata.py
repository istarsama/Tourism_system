import os
import sys
from datetime import datetime
from pathlib import Path

from sqlmodel import Session, select

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

TEST_DB_PATH = PROJECT_ROOT / "tests" / "tmp_osm_graph_cache_metadata.db"
if TEST_DB_PATH.exists():
    TEST_DB_PATH.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH.as_posix()}"

from database import engine, init_db  # noqa: E402
from models import OSMGraphCache  # noqa: E402
from osm_service import _persist_graph_cache_metadata  # noqa: E402


def main():
    init_db()
    downloaded_at = datetime.now()
    _persist_graph_cache_metadata(
        city="北京",
        transport="walk",
        place_query="Beijing, China",
        graph_path="data/osm_graphs/beijing_walk.graphml",
        node_count=123,
        edge_count=456,
        file_size_bytes=789,
        status="ready",
        last_error=None,
        downloaded_at=downloaded_at,
    )

    with Session(engine) as session:
        cache = session.exec(select(OSMGraphCache)).one()
        assert cache.city == "北京"
        assert cache.transport == "walk"
        assert cache.place_query == "Beijing, China"
        assert cache.node_count == 123
        assert cache.edge_count == 456
        assert cache.file_size_bytes == 789
        assert cache.status == "ready"
        assert cache.downloaded_at is not None

    _persist_graph_cache_metadata(
        city="北京",
        transport="walk",
        place_query="北京市, China",
        graph_path="data/osm_graphs/beijing_walk.graphml",
        node_count=123,
        edge_count=456,
        file_size_bytes=789,
        status="refresh_failed",
        last_error="offline",
        downloaded_at=None,
    )

    with Session(engine) as session:
        caches = session.exec(select(OSMGraphCache)).all()
        assert len(caches) == 1
        assert caches[0].place_query == "北京市, China"
        assert caches[0].status == "refresh_failed"
        assert caches[0].last_error == "offline"
        assert caches[0].downloaded_at is not None

    print("✅ OSM GraphML 缓存元数据写入与更新测试通过")


if __name__ == "__main__":
    main()
