# src/clean_db.py
from sqlalchemy import create_engine, text

# 1. 数据库连接配置 (和你 src/database.py 里的一模一样)
# 格式: mysql+pymysql://用户名:密码@地址:端口/数据库名
DATABASE_URL = "mysql+pymysql://root:root@127.0.0.1:3306/campus_nav"

def delete_diary_table():
    print(f"🔌 正在连接数据库: {DATABASE_URL} ...")
    
    # 创建一个连接引擎
    engine = create_engine(DATABASE_URL)
    
    # 连接到数据库
    with engine.connect() as conn:
        print("🗑️  准备删除 'diary' 表...")
        
        # 执行 SQL 命令：如果有 diary 表，就把它丢弃(Drop)
        # IF EXISTS 防止如果表本来就不存在时报错
        conn.execute(text("DROP TABLE IF EXISTS diary"))
        
        # 强制提交更改 (就像点击了保存按钮)
        conn.commit()
        
        print("✅ 'diary' 表已成功删除！")
        print("🚀 现在你可以重新运行主程序，新表会自动创建。")

if __name__ == "__main__":
    try:
        delete_diary_table()
    except Exception as e:
        print(f"❌ 出错了: {e}")
        print("请检查你的数据库是否启动 (Docker 是否开了?)")