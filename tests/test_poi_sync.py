import os
import sys

from sqlmodel import Session, SQLModel, create_engine, select

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(CURRENT_DIR, "..")
SRC_PATH = os.path.join(PROJECT_ROOT, "src")
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

from models import CampusGraph, Spot, POI, POIAlias, POIGeometry
from poi_service import sync_campus_graph_to_poi


def build_demo_graph() -> CampusGraph:
    graph = CampusGraph()
    graph.add_spot(Spot(id=1001, name="测试景点A", type="spot", x=10, y=20, desc="测试描述A"))
    graph.add_spot(Spot(id=1002, name="测试路点", type="road", x=30, y=40, desc=""))
    return graph


def main():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        stats = sync_campus_graph_to_poi(session, build_demo_graph())
        assert stats["poi_created"] == 1
        assert stats["geometry_created"] == 1

        poi = session.exec(select(POI).where(POI.source == "campus", POI.source_ref == "1001")).first()
        assert poi is not None
        assert poi.legacy_spot_id == 1001

        alias = session.exec(select(POIAlias).where(POIAlias.poi_id == poi.id)).first()
        assert alias is not None
        assert alias.alias == "测试景点A"

        geometry = session.exec(select(POIGeometry).where(POIGeometry.poi_id == poi.id)).first()
        assert geometry is not None
        assert geometry.x_pixel == 10
        assert geometry.y_pixel == 20

    print("✅ POI 同步测试通过")


if __name__ == "__main__":
    main()
