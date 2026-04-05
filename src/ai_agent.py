"""
LangGraph 多智能体编排层。

架构：
┌─────────────────────────────────────────────────────────┐
│  router_node                                            │
│  意图路由智能体：判断 rag / web / chat                    │
└──────────┬──────────────┬────────────────────────────────┘
           │              │              │
      rag  │         web  │       chat   │
           ▼              ▼              ▼
  rag_agent_node   web_agent_node   chat_node
  (RAG 专家)       (Web 专家)       (直接闲聊)
           │              │              │
           └──────────────┴──────────────┘
                          │
                    finalize_node
                    统一输出 {reply, source}

设计原则：
- GraphState (TypedDict) 存储全局状态，图节点通过 state 通信，不用局部变量传递。
- 各专家 Agent 仅通过 .bind_tools([...]) 绑定各自的工具（原生 JSON Schema 工具调用）。
- 工具执行失败后节点通过 state["error"] 记录，由 finalize_node 做降级回复。
- MAX_STEPS 保护防止工具 → LLM 无限循环。
"""

import os
from typing import Any, Dict, List, Literal, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, StateGraph
from loguru import logger
from typing_extensions import TypedDict

# ─────────────────────────────────────────────────
# 配置
# ─────────────────────────────────────────────────
MAX_STEPS: int = int(os.getenv("AI_AGENT_MAX_STEPS", "6"))

# ─────────────────────────────────────────────────
# 全局状态定义
# ─────────────────────────────────────────────────

class GraphState(TypedDict, total=False):
    question: str
    route: Literal["rag", "web", "chat"]
    messages: List[Any]
    used_tools: List[str]
    final_answer: str
    source: str
    error: Optional[str]
    step_count: int


# ─────────────────────────────────────────────────
# 系统提示词
# ─────────────────────────────────────────────────

_ROUTER_SYSTEM = """\
你是旅游问答系统的意图路由器，负责对用户问题分类，输出以下三种标签之一：

- rag   ：问题涉及校园经历、景点介绍、旅游日记、攻略推荐等内部数据库知识
- web   ：问题涉及实时天气、最新新闻、交通状况、当前时事等外部动态信息
- chat  ：纯粹的闲聊、问候、与旅游无关的话题

只输出单个英文标签（rag / web / chat），不要任何其他内容。
"""

_RAG_SYSTEM = """\
你是旅游系统的内部旅游专家智能体，专职处理内部数据查询。

可用数据来源：
- 用户旅游日记（含标题、内容、评分、热度、范围(campus/national)）
- 全国景点数据（含名称、城市、类型、简介、评分）

工作流程：
1. 根据用户问题调用 search_internal_knowledge 工具，获取相关数据。
2. 基于工具返回的真实内容，综合分析后给出详细回答。
3. 若工具返回空或错误，如实告知用户。
4. 不可编造数据库中不存在的信息。
"""

_WEB_SYSTEM = """\
你是旅游系统的外部资讯研究员智能体，专职处理实时信息查询。

你的职责：
- 调用 search_web_knowledge 工具查阅最新的天气、交通、新闻等外部动态。
- 基于工具返回的搜索结果，整合并给出准确回答。
- 若工具未能找到信息，如实告知用户。
- 不可编造不存在的搜索结果。
"""

_CHAT_SYSTEM = """\
你是旅游系统的 AI 助手，负责回应用户的闲聊和日常问候。
回复风格：友好、简洁、有温度。
如果用户问题涉及旅游知识，可以温和引导他们问更具体的问题。
"""


# ─────────────────────────────────────────────────
# 节点：意图路由
# ─────────────────────────────────────────────────

def make_router_node(llm: Any):
    def router_node(state: GraphState) -> GraphState:
        question = state.get("question", "")
        logger.debug("Router 判断意图 question={}", question[:60])
        try:
            resp = llm.invoke([
                SystemMessage(content=_ROUTER_SYSTEM),
                HumanMessage(content=question),
            ])
            raw = (resp.content or "").strip().lower()
            if raw in ("rag", "web", "chat"):
                route = raw
            else:
                # 关键词兜底
                if any(kw in question for kw in ("天气", "新闻", "交通", "实时", "今天", "明天", "最新")):
                    route = "web"
                elif any(kw in question for kw in ("日记", "景点", "推荐", "校园", "攻略", "好吃", "好玩")):
                    route = "rag"
                else:
                    route = "chat"
            logger.info("Router 路由结果 route={} question={}", route, question[:60])
        except Exception as exc:
            logger.warning("Router 调用失败，降级为 chat: {}", exc)
            route = "chat"
        return {**state, "route": route, "step_count": 0, "used_tools": [], "messages": []}
    return router_node


# ─────────────────────────────────────────────────
# 节点：专家 Agent（ReAct over Native Tool Calling）
# ─────────────────────────────────────────────────

def _run_specialist(
    state: GraphState,
    llm: Any,
    tools: List[Any],
    system_prompt: str,
    agent_name: str,
) -> GraphState:
    """通用专家 Agent 节点执行逻辑（Native Tool Calling 循环）。"""
    question = state.get("question", "")
    tool_map = {t.name: t for t in tools}
    llm_with_tools = llm.bind_tools(tools)

    messages: List[Any] = state.get("messages", [])
    if not messages:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=question),
        ]

    used_tools: List[str] = list(state.get("used_tools", []))
    step_count: int = state.get("step_count", 0)

    while step_count < MAX_STEPS:
        step_count += 1
        logger.debug("{} 执行步骤 step={}/{}", agent_name, step_count, MAX_STEPS)
        try:
            response = llm_with_tools.invoke(messages)
        except Exception as exc:
            logger.error("{} LLM 调用失败 step={} error={}", agent_name, step_count, exc)
            return {
                **state,
                "messages": messages,
                "used_tools": used_tools,
                "step_count": step_count,
                "error": f"LLM 调用失败: {exc}",
            }

        messages.append(response)

        # 没有工具调用 → 生成了最终答案
        if not getattr(response, "tool_calls", None):
            final_answer = (response.content or "").strip()
            if not final_answer:
                final_answer = "我没有找到足够的信息来回答您的问题，请换个方式提问。"
            logger.info("{} 完成 steps={}", agent_name, step_count)
            return {
                **state,
                "messages": messages,
                "used_tools": used_tools,
                "step_count": step_count,
                "final_answer": final_answer,
            }

        # 执行每个工具调用
        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call.get("args", {})
            tool_call_id = tool_call["id"]

            if tool_name not in tool_map:
                observation = f"工具 '{tool_name}' 不存在，可用工具: {', '.join(tool_map)}"
                logger.warning("{} 调用了未知工具 tool={}", agent_name, tool_name)
            else:
                query_str = tool_args.get("query", "") or str(tool_args)
                logger.info("{} 调用工具 tool={} query={}", agent_name, tool_name, query_str[:60])
                observation = tool_map[tool_name].invoke(tool_args)
                used_tools.append(tool_name)

            messages.append(ToolMessage(content=str(observation), tool_call_id=tool_call_id))

    # 超出最大步数
    logger.warning("{} 超出最大步数 MAX_STEPS={}", agent_name, MAX_STEPS)
    return {
        **state,
        "messages": messages,
        "used_tools": used_tools,
        "step_count": step_count,
        "error": "超出最大步数限制，无法给出完整回答。",
    }


def make_rag_agent_node(llm: Any, rag_tool):
    def rag_agent_node(state: GraphState) -> GraphState:
        return _run_specialist(
            state=state,
            llm=llm,
            tools=[rag_tool],
            system_prompt=_RAG_SYSTEM,
            agent_name="RAG Agent",
        )
    return rag_agent_node


def make_web_agent_node(llm: Any, web_tool):
    def web_agent_node(state: GraphState) -> GraphState:
        return _run_specialist(
            state=state,
            llm=llm,
            tools=[web_tool],
            system_prompt=_WEB_SYSTEM,
            agent_name="Web Agent",
        )
    return web_agent_node


# ─────────────────────────────────────────────────
# 节点：直接闲聊
# ─────────────────────────────────────────────────

def make_chat_node(llm: Any):
    def chat_node(state: GraphState) -> GraphState:
        question = state.get("question", "")
        logger.debug("Chat 节点回答 question={}", question[:60])
        try:
            response = llm.invoke([
                SystemMessage(content=_CHAT_SYSTEM),
                HumanMessage(content=question),
            ])
            answer = (response.content or "").strip() or "你好！有什么可以帮你的吗？"
        except Exception as exc:
            logger.error("Chat 节点失败 error={}", exc)
            answer = "AI 服务暂时不可用，请稍后重试。"
        return {**state, "final_answer": answer, "used_tools": []}
    return chat_node


# ─────────────────────────────────────────────────
# 节点：最终输出格式化
# ─────────────────────────────────────────────────

def finalize_node(state: GraphState) -> GraphState:
    route = state.get("route", "chat")
    used_tools = state.get("used_tools", [])
    error = state.get("error")
    final_answer = state.get("final_answer", "")

    # 若有错误但无回答，给降级回复
    if not final_answer:
        if error:
            final_answer = f"抱歉，处理您的请求时出现问题：{error}"
        else:
            final_answer = "抱歉，我暂时无法回答这个问题，请换个方式提问。"

    # 构建 source 标签
    has_rag = "search_internal_knowledge" in used_tools
    has_web = "search_web_knowledge" in used_tools
    if has_rag:
        source = "Multi-Agent (内部旅游专家 RAG)"
    elif has_web:
        source = "Multi-Agent (外部资讯研究员 Web)"
    elif route == "chat":
        source = "Multi-Agent (直接闲聊)"
    else:
        source = f"Multi-Agent ({route})"

    return {**state, "final_answer": final_answer, "source": source}


# ─────────────────────────────────────────────────
# 条件边：路由决策
# ─────────────────────────────────────────────────

def route_decision(state: GraphState) -> str:
    return state.get("route", "chat")


# ─────────────────────────────────────────────────
# 图构建工厂
# ─────────────────────────────────────────────────

def build_multi_agent_graph(llm: Any, rag_tool, web_tool) -> Any:
    """
    构建并编译 LangGraph 多智能体图。

    参数：
    - llm: 已初始化的 LLM 实例（ChatOpenAI 或兼容接口）
    - rag_tool: build_rag_tool(session) 返回的原生 LangChain 工具
    - web_tool: build_web_tool(tavily_client, current_time) 返回的原生 LangChain 工具

    返回编译后的 CompiledGraph，可通过 .invoke({"question": "..."}) 调用。
    """
    graph = StateGraph(GraphState)

    # 注册节点
    graph.add_node("router", make_router_node(llm))
    graph.add_node("rag_agent", make_rag_agent_node(llm, rag_tool))
    graph.add_node("web_agent", make_web_agent_node(llm, web_tool))
    graph.add_node("chat", make_chat_node(llm))
    graph.add_node("finalize", finalize_node)

    # 入口
    graph.set_entry_point("router")

    # 条件边：router → rag_agent / web_agent / chat
    graph.add_conditional_edges(
        "router",
        route_decision,
        {"rag": "rag_agent", "web": "web_agent", "chat": "chat"},
    )

    # 所有专家节点 → finalize
    graph.add_edge("rag_agent", "finalize")
    graph.add_edge("web_agent", "finalize")
    graph.add_edge("chat", "finalize")
    graph.add_edge("finalize", END)

    return graph.compile()


# ─────────────────────────────────────────────────
# 公共调用入口（保持与旧 ai.py 调用签名兼容）
# ─────────────────────────────────────────────────

def run_multi_agent(
    llm: Any,
    rag_tool,
    web_tool,
    question: str,
) -> Dict[str, str]:
    """
    执行多智能体图，返回 {"reply": ..., "source": ...}。

    这是 ai.py 的统一入口，保持与旧 run_react_agent 返回格式兼容。
    """
    compiled = build_multi_agent_graph(llm=llm, rag_tool=rag_tool, web_tool=web_tool)
    try:
        result = compiled.invoke({"question": question})
        return {
            "reply": result.get("final_answer", ""),
            "source": result.get("source", "Multi-Agent"),
        }
    except Exception as exc:
        logger.error("Multi-Agent 图执行失败 error={}", exc)
        return {
            "reply": f"AI 服务暂时不可用，请稍后重试。（错误：{exc}）",
            "source": "multi_agent_error",
        }
