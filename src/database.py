from sqlmodel import SQLModel, create_engine, Session

# 1. 配置数据库连接地址
# 格式: mysql+pymysql://用户名:密码@地址:端口/数据库名
# 你的配置: 用户=root, 密码=root, 库名=campus_nav (根据你刚才的 docker 命令)
DATABASE_URL = "mysql+pymysql://root:root@127.0.0.1:3306/campus_nav"

# 2. 创建引擎 (Engine)
# echo=True 表示会在控制台打印出每一句生成的 SQL，方便你开发时调试
engine = create_engine(DATABASE_URL, echo=True)

def init_db():
    """
    初始化数据库表结构
    调用这个函数时，SQLModel 会自动根据你的 Python 类在数据库里创建表
    """
    SQLModel.metadata.create_all(engine)

def get_session():
    """
    提供给 FastAPI 依赖注入使用的数据库会话
    用完会自动关闭连接，防止资源泄露
    """
    with Session(engine) as session:
        yield session