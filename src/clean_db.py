from sqlalchemy import create_engine, inspect, text
from database import DATABASE_URL

def clean_all_tables():
    print(f"🔌 连接数据库: {DATABASE_URL} ...")
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        print("🗑️  正在执行强力清理...")

        # 通过 SQLAlchemy inspector 自动发现所有表，兼容 PostgreSQL / MySQL / SQLite
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        # 按依赖安全顺序：先子表后主表
        priority = ["comment", "diary", "user"]
        ordered = [t for t in priority if t in tables] + [t for t in tables if t not in priority]

        for table in ordered:
            print(f"   - 删除表: {table}")
            conn.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE'))

        conn.commit()
        print("✨ 数据库已清空！旧时代的痕迹已完全抹除。")

if __name__ == "__main__":
    try:
        clean_all_tables()
    except Exception as e:
        print(f"❌ 清理失败: {e}")