import os
import sys
import shutil
from datetime import datetime

from fastapi.testclient import TestClient
from langchain_core.embeddings import Embeddings
from sqlmodel import Session, SQLModel

# =========================================================
# 这份脚本是“向量数据库全链路测试”
# 目标：把你刚才做的核心能力尽量都串起来验证一遍：
# 1) 日记发布后触发向量双写（diary.py -> vector_store.upsert_diary）
# 2) 向量检索 + MySQL 回查（ai.py 的 RAG 主链路）
# 3) 全量初始化脚本（tools/init_vector_db.py）
# =========================================================

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(CURRENT_DIR, "..")
SRC_PATH = os.path.join(PROJECT_ROOT, "src")

if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

# ---------------------------------------------------------
# 测试隔离：使用临时 SQLite + 临时向量目录，避免污染你真实数据
# ---------------------------------------------------------
TEST_DB_PATH = os.path.join(PROJECT_ROOT, "tests", "tmp_vector_test.db")
TEST_VECTOR_DIR = os.path.join(PROJECT_ROOT, "tests", "tmp_chroma_test")

if os.path.exists(TEST_DB_PATH):
    os.remove(TEST_DB_PATH)
if os.path.exists(TEST_VECTOR_DIR):
    shutil.rmtree(TEST_VECTOR_DIR, ignore_errors=True)

# 注意：DATABASE_URL 必须在 import database/api 之前设置，才能让 engine 读取到正确路径。
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH.replace('\\', '/')}"
os.environ["VECTOR_DB_PATH"] = TEST_VECTOR_DIR.replace("\\", "/")
# 给一个占位 key，防止某些模块做“空值保护”直接报错。
os.environ["OPENAI_COMPAT_API_KEY"] = "test-key"
os.environ["DEEPSEEK_API_KEY"] = "test-key"

import api  # noqa: E402
import diary  # noqa: E402
import ai  # noqa: E402
import vector_store  # noqa: E402
from database import engine  # noqa: E402
from models import User, NationalSpot  # noqa: E402


class FakeEmbeddings(Embeddings):
    """
    一个“假嵌入模型”：
    - 不联网；
    - 可重复；
    - 维度固定；
    用于在本地测试 Chroma 读写流程。
    """

    def _to_vec(self, text: str) -> list[float]:
        # 把文本简单映射到固定长度向量，确保同样文本每次结果一致。
        vec = [0.0] * 8
        for idx, ch in enumerate(text):
            vec[idx % 8] += (ord(ch) % 97) / 97.0
        # 做个归一化，避免值太大
        norm = sum(abs(v) for v in vec) or 1.0
        return [v / norm for v in vec]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._to_vec(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._to_vec(text)


class FakeLLMResponse:
    def __init__(self, content: str):
        self.content = content


class FakeLLM:
    """
    一个“假大模型”：
    - 分类阶段固定返回 RAG（覆盖 RAG 主链路）；
    - 生成阶段返回可断言文本。
    """

    def invoke(self, prompt):
        text = str(prompt)
        if "只能输出 RAG / NET / NONE" in text:
            return FakeLLMResponse("RAG")
        return FakeLLMResponse("这是测试用RAG回答。")


def seed_base_data() -> tuple[int, int]:
    """
    种子数据：
    - 创建一个测试用户（用于发日记）；
    - 创建一个全国景点（用于 national scope 日记）。
    """
    now = datetime.now()
    with Session(engine) as session:
        user = User(username="vector_tester", password_hash="fake_hash", created_at=now)
        spot = NationalSpot(
            name="测试向量景点",
            type="自然风光",
            latitude=39.9,
            longitude=116.3,
            description="用于向量测试的景点",
            city="北京",
            rating=4.6,
            created_at=now,
            updated_at=now,
        )
        session.add(user)
        session.add(spot)
        session.commit()
        session.refresh(user)
        session.refresh(spot)
        return user.id, spot.id


def main():
    # -----------------------------------------------------
    # 1) 打补丁：把真实 Embedding / LLM 替换成本地假实现
    # -----------------------------------------------------
    vector_store._build_embeddings = lambda: FakeEmbeddings()  # noqa: SLF001
    ai.chat_llm = FakeLLM()

    # -----------------------------------------------------
    # 2) 用 TestClient 启动 app，覆盖登录依赖，模拟已登录用户发帖
    # -----------------------------------------------------
    with TestClient(api.app) as client:
        user_id, national_spot_id = seed_base_data()

        def fake_current_user():
            return User(id=user_id, username="vector_tester", password_hash="fake_hash")

        api.app.dependency_overrides[diary.get_current_user] = fake_current_user
        try:
            # -------------------------------------------------
            # 2.1 发布 campus 日记（应触发 MySQL + 向量双写）
            # -------------------------------------------------
            r1 = client.post(
                "/diaries/",
                json={
                    "scope": "campus",
                    "spot_id": 44,
                    "title": "校园食堂体验",
                    "content": "学一食堂早餐种类很多，性价比不错。",
                    "media_files": [],
                },
            )
            assert r1.status_code == 200, r1.text

            # -------------------------------------------------
            # 2.2 发布 national 日记（再次触发双写）
            # -------------------------------------------------
            r2 = client.post(
                "/diaries/",
                json={
                    "scope": "national",
                    "national_spot_id": national_spot_id,
                    "title": "全国景点游记",
                    "content": "这个景点风景很美，交通也方便。",
                    "media_files": [],
                },
            )
            assert r2.status_code == 200, r2.text

            # -------------------------------------------------
            # 3) 验证向量检索函数可返回 metadata（mysql_id/type）
            # -------------------------------------------------
            metadatas = vector_store.query_relevant_metadata("食堂 推荐", k=5)
            assert isinstance(metadatas, list)
            assert len(metadatas) >= 1
            assert any(("mysql_id" in md and "type" in md) for md in metadatas)

            # -------------------------------------------------
            # 4) 验证 ai /rag_chat 走 RAG 主链路（向量检索 + MySQL回查）
            # -------------------------------------------------
            rag_resp = client.post("/ai/rag_chat", json={"message": "根据日记推荐一下食堂"})
            assert rag_resp.status_code == 200, rag_resp.text
            rag_data = rag_resp.json()
            assert "RAG" in rag_data.get("source", "")
            assert "测试用RAG回答" in rag_data.get("reply", "")

            # -------------------------------------------------
            # 5) 验证全量初始化脚本可执行（使用同一套 fake embedding）
            # -------------------------------------------------
            # 注意：这里直接 import 脚本并调用 main，相当于“脚本功能测试”。
            import importlib.util

            script_path = os.path.join(PROJECT_ROOT, "tools", "init_vector_db.py")
            spec = importlib.util.spec_from_file_location("init_vector_db_test_module", script_path)
            module = importlib.util.module_from_spec(spec)
            assert spec and spec.loader
            spec.loader.exec_module(module)

            # 脚本内部会 import vector_store，这里再打一次补丁，确保仍使用 fake embedding。
            module.vector_store = vector_store
            module.build_full_index_from_db = vector_store.build_full_index_from_db
            module.main()
        finally:
            api.app.dependency_overrides.pop(diary.get_current_user, None)

    print("✅ 向量数据库全链路测试通过")

    # ---------------------------------------------------------
    # 6) 收尾清理（Windows 常见文件锁问题要特别处理）
    # ---------------------------------------------------------
    # 先主动释放 SQLAlchemy 连接池，避免 SQLite 文件还被占用。
    engine.dispose()

    # 再尝试删除临时 SQLite 文件：
    # 如果仍被占用，不让测试失败，只打印提醒（避免“功能通过但脚本失败”的假阴性）。
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except PermissionError:
            print(f"⚠️ 临时数据库文件仍被占用，跳过删除: {TEST_DB_PATH}")

    # 向量目录即使某些文件占用，也尽量容错清理。
    if os.path.exists(TEST_VECTOR_DIR):
        shutil.rmtree(TEST_VECTOR_DIR, ignore_errors=True)


if __name__ == "__main__":
    main()
