# src/create_tables.py
from database import init_db
# 必须导入所有 table=True 模型，SQLModel 才能识别到它们并建表
from models import (
    User,
    Diary,
    Comment,
    POI,
    POIAlias,
    POIGeometry,
    RouteCache,
    OSMGraphCache,
    NationalSpot,
    NationalSpotXHSNote,
    MapConfig,
)

if __name__ == "__main__":
    print("⏳ 正在连接数据库并创建表...")
    try:
        init_db()
        print("✅ 成功！所有数据库表已创建/校验完成。")
    except Exception as e:
        print(f"❌ 创建失败: {e}")
