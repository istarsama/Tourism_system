"""
升级数据库表结构（兼容历史版本）
1) diary 长文本字段升级
2) diary 增加 scope / national_spot_id 字段
3) diary.spot_id 调整为可空以支持 national 日记
"""
import os
import sys

from sqlmodel import create_engine, text

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(CURRENT_DIR, "..", "..")
SRC_PATH = os.path.join(PROJECT_ROOT, "src")
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

from database import DATABASE_URL


def _column_exists(conn, table_name: str, column_name: str) -> bool:
    result = conn.execute(text(f"SHOW COLUMNS FROM {table_name} LIKE :col"), {"col": column_name}).first()
    return result is not None


def upgrade_diary_table():
    print("🔧 开始升级 diary 表结构...")
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        try:
            # 1. 修改 content 字段为 TEXT
            print("   📝 修改 content 字段为 TEXT 类型...")
            conn.execute(text("ALTER TABLE diary MODIFY COLUMN content TEXT NOT NULL"))
            
            # 2. 修改 title 字段长度
            print("   📝 修改 title 字段为 VARCHAR(500)...")
            conn.execute(text("ALTER TABLE diary MODIFY COLUMN title VARCHAR(500) NOT NULL"))
            
            # 3. 修改 media_json 字段为 TEXT
            print("   📝 修改 media_json 字段为 TEXT 类型...")
            conn.execute(text("ALTER TABLE diary MODIFY COLUMN media_json TEXT NOT NULL"))

            # 4. spot_id 改为可空（兼容 national 日记）
            print("   📝 调整 spot_id 字段为可空...")
            conn.execute(text("ALTER TABLE diary MODIFY COLUMN spot_id INT NULL"))

            # 5. 新增 scope 字段（若不存在）
            if not _column_exists(conn, "diary", "scope"):
                print("   🧭 新增 scope 字段...")
                conn.execute(text("ALTER TABLE diary ADD COLUMN scope VARCHAR(20) NOT NULL DEFAULT 'campus'"))
            else:
                print("   ✅ scope 字段已存在，跳过")

            # 6. 新增 national_spot_id 字段（若不存在）
            if not _column_exists(conn, "diary", "national_spot_id"):
                print("   🌏 新增 national_spot_id 字段...")
                conn.execute(text("ALTER TABLE diary ADD COLUMN national_spot_id INT NULL"))
            else:
                print("   ✅ national_spot_id 字段已存在，跳过")
             
            conn.commit()
            print("✅ 表结构升级成功！")
            
            # 验证修改
            print("\n📊 当前表结构:")
            result = conn.execute(text('DESCRIBE diary'))
            print(f"{'字段名':<20} {'类型':<30}")
            print("-"*50)
            for row in result:
                print(f"{row[0]:<20} {row[1]:<30}")
                
        except Exception as e:
            print(f"❌ 升级失败: {e}")
            conn.rollback()

if __name__ == "__main__":
    upgrade_diary_table()
