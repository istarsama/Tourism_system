"""
AI Agent 工具层：定义所有可被 ReAct Agent 调用的工具。

工具设计原则：
- name: 唯一英文标识，下划线分隔
- description: 精准说明用途，让 LLM 自主决策何时调用
- 工具内部异常统一捕获后返回可读错误文本，不向 Agent 抛出异常
"""

from typing import Callable, List, Optional

from loguru import logger
from sqlmodel import Session

from models import Diary, NationalSpot
from vector_store import query_relevant_metadata


def _safe_text(value) -> str:
    return str(value) if value is not None else ""


class AgentTool:
    """单个可被 ReAct Agent 调用的工具。"""

    def __init__(self, name: str, description: str, func: Callable[[str], str]) -> None:
        self.name = name
        self.description = description
        self._func = func

    def run(self, query: str) -> str:
        """执行工具逻辑，内部异常统一转为可读错误信息。"""
        try:
            return self._func(query)
        except Exception as exc:
            logger.error("工具执行失败 tool={} error={}", self.name, str(exc))
            return f"[工具执行失败: {str(exc)}]"


def build_rag_tool(session: Session) -> AgentTool:
    """
    内部知识检索工具：向量检索 + MySQL 回查。

    先用语义向量找到相关文档 ID，再回查 MySQL 拿完整字段，
    保证回答依据的是数据库最新完整数据。
    """

    def _rag_func(query: str) -> str:
        metadatas = query_relevant_metadata(query=query, k=6)
        if not metadatas:
            return "未检索到相关内部数据。"

        lines: List[str] = []
        seen: set = set()

        for md in metadatas:
            mysql_id = md.get("mysql_id")
            doc_type = md.get("type")
            if mysql_id is None or not doc_type:
                continue
            unique_key = f"{doc_type}:{mysql_id}"
            if unique_key in seen:
                continue
            seen.add(unique_key)

            if doc_type == "diary":
                diary = session.get(Diary, int(mysql_id))
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
                spot = session.get(NationalSpot, int(mysql_id))
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

        return "\n\n".join(lines) if lines else "命中向量结果，但回查 MySQL 未找到可用详情。"

    return AgentTool(
        name="search_internal_knowledge",
        description=(
            "检索系统内部知识库（用户日记、全国景点信息）。"
            "当用户询问校园经验、景点介绍、旅游攻略、日记推荐等内部知识时使用。"
        ),
        func=_rag_func,
    )


def build_web_tool(tavily_client: Optional[object], current_time: str) -> AgentTool:
    """
    外部联网搜索工具：调用 Tavily 检索实时信息。

    若未配置 TAVILY_API_KEY，工具仍可注册但会返回无法搜索的提示。
    """

    def _web_func(query: str) -> str:
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
            lines = []
            for idx, item in enumerate(results, start=1):
                lines.append(
                    f"【联网来源{idx}】{item.get('content', '')} (链接: {item.get('url', '')})"
                )
            return "\n".join(lines)
        except Exception as exc:
            logger.error("联网搜索失败 error={}", str(exc))
            return f"联网搜索失败: {str(exc)}"

    return AgentTool(
        name="search_web_knowledge",
        description=(
            "联网检索实时外部信息。"
            "当用户询问天气、新闻、实时动态、外部时事等内部数据库没有的信息时使用。"
        ),
        func=_web_func,
    )


def build_all_tools(
    session: Session,
    tavily_client: Optional[object],
    current_time: str,
) -> List[AgentTool]:
    """组合当前请求可用的全部工具列表。"""
    tools: List[AgentTool] = [build_rag_tool(session)]
    tools.append(build_web_tool(tavily_client, current_time))
    return tools
