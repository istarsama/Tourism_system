"""
AI Agent 工具层：为 LangGraph 多智能体定义原生工具。

设计原则：
- 使用 LangChain @tool 装饰器，支持 .bind_tools([...]) 原生 JSON Schema 工具调用。
- build_rag_tool 返回只负责内部知识检索的工具（向量检索 + 数据库回查）。
- build_web_tool 返回只负责外部联网搜索的工具（Tavily）。
- 工具内部失败通过返回带 [ERROR] 前缀的字符串告知 Agent，不向图节点抛出异常。
"""

from typing import List, Optional

from langchain_core.tools import BaseTool, tool
from loguru import logger
from sqlmodel import Session

from models import Diary, NationalSpot
from vector_store import query_relevant_metadata


def _safe_text(value) -> str:
    return str(value) if value is not None else ""


def build_rag_tool(session: Session) -> BaseTool:
    """
    内部知识检索工具：向量检索 + 数据库回查。

    先用语义向量找到相关文档 ID，再回查数据库拿完整字段，
    保证回答依据的是数据库最新完整数据。
    """

    @tool
    def search_internal_knowledge(query: str) -> str:
        """检索系统内部知识库（用户旅游日记、全国景点信息）。
        当用户询问校园经验、景点介绍、旅游攻略、日记推荐等内部知识时调用。
        query 参数为中文检索关键词。
        """
        try:
            metadatas = query_relevant_metadata(query=query, k=6)
        except Exception as exc:
            logger.error("RAG 向量检索失败 error={}", str(exc))
            return f"[ERROR] 向量检索失败: {exc}"

        if not metadatas:
            return "未检索到相关内部数据。"

        lines: List[str] = []
        seen: set = set()

        for md in metadatas:
            db_id = md.get("db_id")
            doc_type = md.get("type")
            if db_id is None or not doc_type:
                continue
            unique_key = f"{doc_type}:{db_id}"
            if unique_key in seen:
                continue
            seen.add(unique_key)

            if doc_type == "diary":
                diary = session.get(Diary, int(db_id))
                if not diary:
                    continue
                lines.append(
                    "\n".join([
                        "【内部来源-日记】",
                        f"ID: {diary.id}",
                        f"范围: {diary.scope}",
                        f"标题: {diary.title}",
                        f"内容: {diary.content}",
                        f"评分: {diary.score}",
                        f"热度: {diary.view_count}",
                    ])
                )
            elif doc_type == "national_spot":
                spot = session.get(NationalSpot, int(db_id))
                if not spot:
                    continue
                lines.append(
                    "\n".join([
                        "【内部来源-全国景点】",
                        f"ID: {spot.id}",
                        f"名称: {spot.name}",
                        f"城市: {spot.city}",
                        f"类型: {spot.type}",
                        f"简介: {spot.description or '无'}",
                        f"评分: {spot.rating}",
                    ])
                )

        return "\n\n".join(lines) if lines else "命中向量结果，但回查数据库未找到可用详情。"

    return search_internal_knowledge


def build_web_tool(tavily_client: Optional[object], current_time: str) -> BaseTool:
    """
    外部联网搜索工具：调用 Tavily 检索实时信息。

    若未配置 TAVILY_API_KEY，工具仍可注册但会返回无法搜索的提示。
    """

    @tool
    def search_web_knowledge(query: str) -> str:
        """联网检索实时外部信息（天气、新闻、交通动态等）。
        当用户询问天气、新闻、实时动态、外部时事等内部数据库没有的信息时调用。
        query 参数为中文检索关键词。
        """
        if not tavily_client:
            return "未配置 TAVILY_API_KEY，无法进行联网搜索。"
        try:
            response = tavily_client.search(
                query=f"{query}（当前时间: {current_time}）",
                search_depth="basic",
                max_results=3,
            )
            results = response.get("results", [])
            if not results:
                return "联网搜索未找到可用结果。"
            parts = []
            for idx, item in enumerate(results, start=1):
                parts.append(
                    f"【联网来源{idx}】{item.get('content', '')} (链接: {item.get('url', '')})"
                )
            return "\n".join(parts)
        except Exception as exc:
            logger.error("联网搜索失败 error={}", str(exc))
            return f"[ERROR] 联网搜索失败: {exc}"

    return search_web_knowledge
