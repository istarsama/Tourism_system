"""
升级数据库表结构（兼容历史版本）
1) diary 长文本字段升级
2) diary 增加 scope / national_spot_id 字段
3) diary.spot_id 调整为可空以支持 national 日记

兼容 PostgreSQL / MySQL / SQLite。
"""
import os
import sys

from sqlalchemy import inspect
from sqlmodel import SQLModel, create_engine, text

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(CURRENT_DIR, "..", "..")
SRC_PATH = os.path.join(PROJECT_ROOT, "src")
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

from database import DATABASE_URL
import models  # noqa: F401  # 导入模型以注册 SQLModel metadata


def _table_exists(engine, table_name: str) -> bool:
    """方言无关的表存在性检测。"""

    insp = inspect(engine)
    return table_name in insp.get_table_names()


def _ensure_column(conn, engine, table_name: str, column_name: str, definition_sql: str) -> None:
    """若列不存在，则执行 ALTER TABLE ADD COLUMN。"""

    if _column_exists(conn, engine, table_name, column_name):
        print(f"   ✅ {table_name}.{column_name} 已存在，跳过")
        return
    print(f"   📝 新增 {table_name}.{column_name} 字段...")
    conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition_sql}"))


def _column_exists(conn, engine, table_name: str, column_name: str) -> bool:
    """方言无关的列存在性检测"""
    insp = inspect(engine)
    columns = [c["name"] for c in insp.get_columns(table_name)]
    return column_name in columns


def _is_postgres(engine) -> bool:
    return engine.dialect.name == "postgresql"


def upgrade_diary_table():
    print("🔧 开始升级 diary 表结构...")
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        try:
            if _is_postgres(engine):
                # PostgreSQL: ALTER COLUMN ... TYPE
                print("   📝 修改 content 字段为 TEXT 类型...")
                conn.execute(text("ALTER TABLE diary ALTER COLUMN content TYPE TEXT"))

                print("   📝 修改 title 字段为 VARCHAR(500)...")
                conn.execute(text("ALTER TABLE diary ALTER COLUMN title TYPE VARCHAR(500)"))

                print("   📝 修改 media_json 字段为 TEXT 类型...")
                conn.execute(text("ALTER TABLE diary ALTER COLUMN media_json TYPE TEXT"))

                print("   📝 调整 spot_id 字段为可空...")
                conn.execute(text("ALTER TABLE diary ALTER COLUMN spot_id DROP NOT NULL"))
            else:
                # MySQL: MODIFY COLUMN
                print("   📝 修改 content 字段为 TEXT 类型...")
                conn.execute(text("ALTER TABLE diary MODIFY COLUMN content TEXT NOT NULL"))

                print("   📝 修改 title 字段为 VARCHAR(500)...")
                conn.execute(text("ALTER TABLE diary MODIFY COLUMN title VARCHAR(500) NOT NULL"))

                print("   📝 修改 media_json 字段为 TEXT 类型...")
                conn.execute(text("ALTER TABLE diary MODIFY COLUMN media_json TEXT NOT NULL"))

                print("   📝 调整 spot_id 字段为可空...")
                conn.execute(text("ALTER TABLE diary MODIFY COLUMN spot_id INT NULL"))

            # 新增 scope 字段（若不存在）
            if not _column_exists(conn, engine, "diary", "scope"):
                print("   🧭 新增 scope 字段...")
                conn.execute(text("ALTER TABLE diary ADD COLUMN scope VARCHAR(20) NOT NULL DEFAULT 'campus'"))
            else:
                print("   ✅ scope 字段已存在，跳过")

            # 新增 national_spot_id 字段（若不存在）
            if not _column_exists(conn, engine, "diary", "national_spot_id"):
                print("   🌏 新增 national_spot_id 字段...")
                conn.execute(text("ALTER TABLE diary ADD COLUMN national_spot_id INT NULL"))
            else:
                print("   ✅ national_spot_id 字段已存在，跳过")

            if _table_exists(engine, "national_spot"):
                print("\n🌸 检查 national_spot 表的小红书扩展字段...")
                _ensure_column(conn, engine, "national_spot", "province", "VARCHAR(100)")
                _ensure_column(conn, engine, "national_spot", "flower_type", "VARCHAR(100)")
                _ensure_column(conn, engine, "national_spot", "best_season", "VARCHAR(100)")
                _ensure_column(conn, engine, "national_spot", "search_keywords_json", "TEXT NOT NULL DEFAULT '[]'")
                _ensure_column(conn, engine, "national_spot", "xhs_query", "VARCHAR(255)")
                _ensure_column(conn, engine, "national_spot", "source", "VARCHAR(50) NOT NULL DEFAULT 'seed'")
                _ensure_column(conn, engine, "national_spot", "xhs_fetch_status", "VARCHAR(30) NOT NULL DEFAULT 'pending'")
                _ensure_column(conn, engine, "national_spot", "xhs_fetch_message", "TEXT")
                _ensure_column(conn, engine, "national_spot", "xhs_cookie_needs_refresh", "BOOLEAN NOT NULL DEFAULT FALSE")
                _ensure_column(conn, engine, "national_spot", "xhs_note_count", "INTEGER NOT NULL DEFAULT 0")
                _ensure_column(conn, engine, "national_spot", "xhs_last_fetched_at", "TIMESTAMP")
            else:
                print("\n⚠️ national_spot 表不存在，跳过字段升级；后续会用 create_all() 自动建表。")

            conn.commit()

            # 新表直接交给 SQLModel metadata 创建，避免重复手写 CREATE TABLE 语句。
            SQLModel.metadata.create_all(engine)
            print("✅ 表结构升级成功！")

            # 验证修改 — 方言无关
            print("\n📊 当前表结构:")
            insp = inspect(engine)
            columns = insp.get_columns("diary")
            print(f"{'字段名':<20} {'类型':<30} {'可空':<10}")
            print("-" * 60)
            for col in columns:
                print(f"{col['name']:<20} {str(col['type']):<30} {'YES' if col['nullable'] else 'NO':<10}")

        except Exception as e:
            print(f"❌ 升级失败: {e}")
            conn.rollback()

if __name__ == "__main__":
    upgrade_diary_table()
