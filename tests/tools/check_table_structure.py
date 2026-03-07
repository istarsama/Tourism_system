from sqlmodel import create_engine, text
from src.database import DATABASE_URL

engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    result = conn.execute(text('DESCRIBE diary'))
    print("\n日记表 (diary) 结构:")
    print("="*70)
    print(f"{'字段名':<20} {'类型':<30} {'可空':<10}")
    print("-"*70)
    for row in result:
        print(f"{row[0]:<20} {row[1]:<30} {row[2]:<10}")
