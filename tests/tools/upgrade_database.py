"""
升级数据库表结构
将 diary.content 字段从 VARCHAR(255) 改为 TEXT
将 diary.title 字段从 VARCHAR(255) 改为 VARCHAR(500)
将 diary.media_json 字段从 VARCHAR(255) 改为 TEXT
"""
from sqlmodel import create_engine, text
from src.database import DATABASE_URL

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
