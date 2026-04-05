import os
from dotenv import load_dotenv
from loguru import logger
from sqlmodel import SQLModel, create_engine, Session

load_dotenv()


def _as_bool(raw: str | None, default: bool) -> bool:
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


# 1. 配置数据库连接地址（可通过 .env 覆盖）
# DATABASE_URL 示例: postgresql+psycopg://campus_user:campus_pass@127.0.0.1:5432/campus_nav
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://campus_user:campus_pass@127.0.0.1:5432/campus_nav")
SQL_ECHO = _as_bool(os.getenv("SQL_ECHO"), False)

# 2. 创建引擎 (Engine)
engine = create_engine(DATABASE_URL, echo=SQL_ECHO, pool_pre_ping=True)

def init_db():
    """
    初始化数据库表结构
    调用这个函数时，SQLModel 会自动根据你的 Python 类在数据库里创建表
    """
    logger.info("初始化数据库表结构...")
    SQLModel.metadata.create_all(engine)
    logger.info("数据库表结构初始化完成。")

def get_session():
    """
    提供给 FastAPI 依赖注入使用的数据库会话
    用完会自动关闭连接，防止资源泄露
    """
    with Session(engine) as session:
        yield session
