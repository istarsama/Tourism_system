from sqlalchemy import inspect
from sqlmodel import create_engine
from src.database import DATABASE_URL

engine = create_engine(DATABASE_URL)
insp = inspect(engine)

# 列出所有表
tables = insp.get_table_names()
print(f"\n📋 数据库中共 {len(tables)} 张表: {', '.join(tables)}")

# 如果 diary 表存在，显示其结构
if "diary" in tables:
    print("\n日记表 (diary) 结构:")
    print("=" * 70)
    print(f"{'字段名':<20} {'类型':<30} {'可空':<10}")
    print("-" * 70)
    for col in insp.get_columns("diary"):
        print(f"{col['name']:<20} {str(col['type']):<30} {'YES' if col['nullable'] else 'NO':<10}")
else:
    print("\n⚠️ diary 表不存在，请先启动后端让 create_all() 初始化表结构。")
