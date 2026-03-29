"""
这个模块负责“向量库相关”的所有操作。

为什么要单独做这个文件？
1) 让 diary.py、ai.py 不需要关心 Chroma/LangChain 的底层细节；
2) 避免后续功能扩展时，把向量逻辑散落在多个文件里；
3) 统一管理配置项（路径、模型、API Key 等）。
"""

import hashlib
import math
import os
from typing import Any, Dict, List, Literal, Optional, Sequence

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings
from loguru import logger
from openai import NotFoundError
from sqlmodel import Session, select

from models import Diary, NationalSpot

# 先加载 .env，确保后面的 os.getenv 能读到环境变量。
load_dotenv()

# 约束文档类型：目前我们只支持“日记”和“全国景点”两类。
VectorDocType = Literal["diary", "national_spot"]

# ------------------------------
# 统一配置区（都可通过 .env 覆盖）
# ------------------------------
VECTOR_COLLECTION_NAME = os.getenv("VECTOR_COLLECTION_NAME", "tourism_rag")
VECTOR_DB_PATH = os.getenv("VECTOR_DB_PATH", "./data/chroma")
OPENAI_COMPAT_BASE_URL = os.getenv("OPENAI_COMPAT_BASE_URL", "https://api.deepseek.com")
OPENAI_COMPAT_API_KEY = os.getenv("OPENAI_COMPAT_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
EMBEDDING_BACKEND = os.getenv("EMBEDDING_BACKEND", "openai").strip().lower()
EMBEDDING_BASE_URL = os.getenv("EMBEDDING_BASE_URL") or OPENAI_COMPAT_BASE_URL
EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY") or OPENAI_COMPAT_API_KEY
EMBEDDING_VECTOR_SIZE = int(os.getenv("EMBEDDING_VECTOR_SIZE", "256"))


def _build_doc_id(doc_type: VectorDocType, mysql_id: int) -> str:
    """
    生成稳定且可复用的文档 ID。

    这么做的好处是：
    - 重跑初始化脚本时不会产生重复脏数据；
    - 后续做“增量更新”时可以直接覆盖同一条文档。
    """
    if doc_type == "diary":
        return f"diary:{mysql_id}"
    return f"spot:{mysql_id}"


class _LocalHashEmbeddings(Embeddings):
    """
    本地哈希嵌入（离线可用）。

    用途：
    - 仅用于“本地开发/无外部 embedding API”场景；
    - 语义效果弱于真实 embedding 模型，但可保证流程可跑通。
    """

    def __init__(self, vector_size: int = 256) -> None:
        if vector_size <= 0:
            raise ValueError("EMBEDDING_VECTOR_SIZE 必须为正整数。")
        self.vector_size = vector_size

    def _embed_text(self, text: str) -> List[float]:
        vec = [0.0] * self.vector_size
        normalized = (text or "").strip()
        if not normalized:
            return vec

        for idx, token in enumerate(normalized.split()):
            digest = hashlib.sha256(f"{idx}:{token}".encode("utf-8")).digest()
            bucket = int.from_bytes(digest[:4], byteorder="little", signed=False) % self.vector_size
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            weight = 0.5 + digest[5] / 255.0
            vec[bucket] += sign * weight

        norm = math.sqrt(sum(v * v for v in vec))
        if norm <= 0.0:
            return vec
        return [v / norm for v in vec]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._embed_text(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._embed_text(text)


def _build_embeddings() -> Embeddings:
    """
    创建 LangChain 的 Embedding 客户端（OpenAI 兼容协议）。

    注意：
    - 这里使用 OPENAI_COMPAT_* 配置，能对接 OpenAI 兼容服务；
    - 若用户没配置 API Key，明确抛错，避免后续出现难定位的空结果。
    """
    if EMBEDDING_BACKEND == "local_hash":
        logger.warning("当前使用本地哈希向量（EMBEDDING_BACKEND=local_hash），检索语义效果会弱于真实 embedding API。")
        return _LocalHashEmbeddings(vector_size=EMBEDDING_VECTOR_SIZE)

    if EMBEDDING_BACKEND != "openai":
        raise ValueError("EMBEDDING_BACKEND 仅支持 openai 或 local_hash。")
    if not EMBEDDING_API_KEY:
        raise ValueError("缺少 EMBEDDING_API_KEY（或 OPENAI_COMPAT_API_KEY/DEEPSEEK_API_KEY），无法初始化嵌入模型。")

    return OpenAIEmbeddings(
        model=EMBEDDING_MODEL,
        api_key=EMBEDDING_API_KEY,
        base_url=EMBEDDING_BASE_URL,
    )


def _raise_embedding_404_context(exc: NotFoundError) -> None:
    raise RuntimeError(
        "Embedding API 返回 404：通常是 base_url 或 embedding 模型不匹配。"
        "当前可检查/设置：EMBEDDING_BASE_URL、EMBEDDING_MODEL、EMBEDDING_API_KEY。"
        "如果你只配置了 DeepSeek 聊天密钥且无 embedding 服务，可改用 EMBEDDING_BACKEND=local_hash。"
    ) from exc


def _build_store() -> Chroma:
    """
    创建 Chroma 向量库实例。

    这里使用本地持久化目录（persist_directory），
    所以服务重启后数据不会丢失。
    """
    os.makedirs(VECTOR_DB_PATH, exist_ok=True)
    return Chroma(
        collection_name=VECTOR_COLLECTION_NAME,
        persist_directory=VECTOR_DB_PATH,
        embedding_function=_build_embeddings(),
    )


def _safe_text(value: Optional[Any]) -> str:
    """
    把可空字段统一转为字符串，避免拼接文本时报错。
    """
    return str(value) if value is not None else ""


def build_diary_document(diary: Diary) -> Document:
    """
    把 Diary ORM 对象转换为向量文档 Document。

    page_content: 给 embedding 模型看的文本（尽量包含检索有价值字段）
    metadata:     给业务回查用的数据（必须包含 mysql_id + type）
    id:           稳定文档 ID（用于幂等 upsert）
    """
    if diary.id is None:
        raise ValueError("Diary 还没有 id，不能构建向量文档。")

    content = "\n".join(
        [
            "类型: 日记",
            f"标题: {_safe_text(diary.title)}",
            f"范围: {_safe_text(diary.scope)}",
            f"内容: {_safe_text(diary.content)}",
            f"评分: {_safe_text(diary.score)}",
            f"浏览量: {_safe_text(diary.view_count)}",
        ]
    )

    metadata = {
        "mysql_id": int(diary.id),
        "type": "diary",
        "scope": diary.scope,
        "spot_id": diary.spot_id,
        "national_spot_id": diary.national_spot_id,
    }

    return Document(
        page_content=content,
        metadata=metadata,
        id=_build_doc_id("diary", int(diary.id)),
    )


def build_national_spot_document(spot: NationalSpot) -> Document:
    """
    把 NationalSpot ORM 对象转换为向量文档。
    """
    if spot.id is None:
        raise ValueError("NationalSpot 还没有 id，不能构建向量文档。")

    content = "\n".join(
        [
            "类型: 全国景点",
            f"名称: {_safe_text(spot.name)}",
            f"城市: {_safe_text(spot.city)}",
            f"分类: {_safe_text(spot.type)}",
            f"简介: {_safe_text(spot.description)}",
            f"评分: {_safe_text(spot.rating)}",
            f"坐标: ({_safe_text(spot.latitude)}, {_safe_text(spot.longitude)})",
        ]
    )

    metadata = {
        "mysql_id": int(spot.id),
        "type": "national_spot",
        "city": spot.city,
        "spot_type": spot.type,
    }

    return Document(
        page_content=content,
        metadata=metadata,
        id=_build_doc_id("national_spot", int(spot.id)),
    )


def upsert_documents(documents: Sequence[Document]) -> None:
    """
    批量写入/更新文档到向量库。

    说明：
    - LangChain 的 Chroma.add_documents 在文档 ID 重复时会覆盖（即 upsert 语义）。
    - 如果 documents 为空，直接返回，避免无意义调用。
    """
    if not documents:
        return
    store = _build_store()
    try:
        store.add_documents(documents=documents)
    except NotFoundError as exc:
        _raise_embedding_404_context(exc)


def upsert_diary(diary: Diary) -> None:
    """
    对单篇日记做增量 upsert（发布新日记后直接调用）。
    """
    upsert_documents([build_diary_document(diary)])


def upsert_national_spot(spot: NationalSpot) -> None:
    """
    对单个全国景点做增量 upsert（预留给后续管理后台使用）。
    """
    upsert_documents([build_national_spot_document(spot)])


def query_relevant_metadata(query: str, k: int = 6) -> List[Dict[str, Any]]:
    """
    语义检索入口：只返回 metadata，供 ai.py 再回查 MySQL 详情。

    为什么不直接把 page_content 给 LLM？
    - 项目已约定“检索 -> mysql_id 回查 -> 再回答”的链路，
      这样可以保证回答依据的是数据库最新完整数据。
    """
    store = _build_store()
    try:
        docs = store.similarity_search(query=query, k=k)
    except NotFoundError as exc:
        _raise_embedding_404_context(exc)
    return [doc.metadata for doc in docs if doc.metadata]


def build_full_index_from_db(session: Session, include_inactive_national_spot: bool = False) -> int:
    """
    全量初始化索引：读取 MySQL 中的 Diary + NationalSpot，批量写入向量库。

    参数：
    - include_inactive_national_spot=False：默认只灌入 active 景点。

    返回：
    - 写入文档条数（便于脚本输出统计）。
    """
    documents: List[Document] = []

    # 1) 读取全部日记
    diaries = session.exec(select(Diary)).all()
    for diary in diaries:
        if diary.id is None:
            continue
        documents.append(build_diary_document(diary))

    # 2) 读取全国景点（可选择是否包含下线数据）
    stmt = select(NationalSpot)
    if not include_inactive_national_spot:
        stmt = stmt.where(NationalSpot.is_active == True)  # noqa: E712
    spots = session.exec(stmt).all()
    for spot in spots:
        if spot.id is None:
            continue
        documents.append(build_national_spot_document(spot))

    # 3) 一次性写入向量库
    upsert_documents(documents)
    logger.info("向量库全量初始化完成，文档数={}", len(documents))
    return len(documents)
