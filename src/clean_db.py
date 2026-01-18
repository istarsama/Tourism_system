from sqlalchemy import create_engine, text
from database import DATABASE_URL # 直接复用 database.py 里的配置

def clean_all_tables():
    print(f"🔌 连接数据库: {DATABASE_URL} ...")
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        print("🗑️  正在执行强力清理...")
        
        # 1. 禁用外键检查 (防止删除时因为关联报错)
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        
        # 2. 按顺序删除所有表
        # 注意：如果有其他表，也要加在这里
        tables = ["comment", "diary", "user"] 
        for table in tables:
            print(f"   - 删除表: {table}")
            conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
            
        # 3. 恢复外键检查
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
        
        conn.commit()
        print("✨ 数据库已清空！旧时代的痕迹已完全抹除。")

if __name__ == "__main__":
    try:
        clean_all_tables()
    except Exception as e:
        print(f"❌ 清理失败: {e}")