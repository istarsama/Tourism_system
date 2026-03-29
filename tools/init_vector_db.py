"""
向量库初始化脚本（一次性/可重跑）。

这个脚本做的事情很简单：
1) 连接当前 DATABASE_URL 对应的 MySQL/SQLite；
2) 读取历史 Diary + NationalSpot；
3) 调用 embedding，把文档写入 Chroma；
4) 输出统计信息，便于你确认是否成功。

运行方式：
    uv run python tools/init_vector_db.py
"""

import os
import sys

from dotenv import load_dotenv
from loguru import logger
from sqlmodel import Session

# ------------------------------------------------------------
# 关键路径处理：
# tools/ 下脚本默认不能直接 import src 下模块，
# 所以这里把 src 目录主动塞进 sys.path。
# ------------------------------------------------------------
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(CURRENT_DIR, "..")
SRC_PATH = os.path.join(PROJECT_ROOT, "src")

if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

# 这里的 import 必须放在路径处理后面，否则会找不到模块。
from database import engine  # noqa: E402
from vector_store import build_full_index_from_db  # noqa: E402


def main() -> None:
    """
    脚本主入口。
    """
    # 加载 .env，确保 DATABASE_URL/OPENAI_COMPAT_API_KEY 等配置生效。
    load_dotenv()
    logger.info("开始执行向量库全量初始化...")

    # 用项目统一的 engine 建会话，避免重复造连接配置。
    with Session(engine) as session:
        total = build_full_index_from_db(session=session)

    logger.info("向量库初始化完成，总写入文档 {} 条", total)


if __name__ == "__main__":
    main()
