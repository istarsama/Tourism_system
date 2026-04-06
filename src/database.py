import os
from dotenv import load_dotenv
from loguru import logger
from sqlalchemy import inspect, text
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

_NATIONAL_SPOT_COMPAT_COLUMNS: tuple[tuple[str, str], ...] = (
    ("province", "VARCHAR(100)"),
    ("flower_type", "VARCHAR(100)"),
    ("best_season", "VARCHAR(100)"),
    ("search_keywords_json", "TEXT NOT NULL DEFAULT '[]'"),
    ("xhs_query", "VARCHAR(255)"),
    ("source", "VARCHAR(50) NOT NULL DEFAULT 'seed'"),
    ("xhs_fetch_status", "VARCHAR(30) NOT NULL DEFAULT 'pending'"),
    ("xhs_fetch_message", "TEXT"),
    ("xhs_cookie_needs_refresh", "BOOLEAN NOT NULL DEFAULT FALSE"),
    ("xhs_note_count", "INTEGER NOT NULL DEFAULT 0"),
    ("xhs_last_fetched_at", "TIMESTAMP"),
)


def _ensure_compat_schema() -> None:
    """
    为历史库补齐新增列。

    SQLModel.create_all() 只会创建缺失的表，不会修改已经存在的旧表。
    因此只要数据库里还保留着早期版本的 national_spot 表，就必须在启动时做一次“只增列”的兼容升级，
    否则 ORM 在 SELECT 新字段时会直接触发 UndefinedColumn。
    """

    existing_tables = set(inspect(engine).get_table_names())
    with engine.begin() as connection:
        if "national_spot" not in existing_tables:
            return

        existing_columns = {
            column["name"]
            for column in inspect(connection).get_columns("national_spot")
        }
        for column_name, definition_sql in _NATIONAL_SPOT_COMPAT_COLUMNS:
            if column_name in existing_columns:
                continue

            logger.warning("检测到旧版表结构，正在补齐字段 national_spot.{}", column_name)
            connection.execute(
                text(f"ALTER TABLE national_spot ADD COLUMN {column_name} {definition_sql}")
            )

def init_db():
    """
    初始化数据库表结构
    调用这个函数时，SQLModel 会自动根据你的 Python 类在数据库里创建表
    """
    # 延迟导入确保 metadata 已注册完整；这样即使调用方只 import database，
    # init_db() 也能正确创建/校验 national_spot 等后续新增的表。
    import models  # noqa: F401

    logger.info("初始化数据库表结构...")
    SQLModel.metadata.create_all(engine)
    _ensure_compat_schema()
    logger.info("数据库表结构初始化完成。")

def get_session():
    """
    提供给 FastAPI 依赖注入使用的数据库会话
    用完会自动关闭连接，防止资源泄露
    """
    with Session(engine) as session:
        yield session
