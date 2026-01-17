# src/create_tables.py
from database import init_db
# 必须导入这两个模型，SQLModel 才能识别到它们并建表
from models import User, Diary 

if __name__ == "__main__":
    print("⏳ 正在连接数据库并创建表...")
    try:
        init_db()
        print("✅ 成功！User 和 Diary 表已创建。")
    except Exception as e:
        print(f"❌ 创建失败: {e}")