"""
ReAct Agent 运行时（Reasoning + Acting 循环）。

设计原则：
- 通过工具 description 让 LLM 自主决策调用哪个工具
- 强制 max_iterations 上限防止死循环消耗 token
- 对解析失败、未知工具、超迭代等情况有明确的日志与兜底处理
"""

import os
import re
from typing import Any, Dict, List, Set

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from loguru import logger

# ----------------------------------------
# 配置：可通过 .env 中 AI_AGENT_MAX_ITERATIONS 覆盖
# ----------------------------------------
MAX_ITERATIONS: int = int(os.getenv("AI_AGENT_MAX_ITERATIONS", "5"))

# ReAct 系统提示词模板（{tools_desc} 由 build 时填入）
_REACT_SYSTEM_TEMPLATE = """\
你是旅游系统 AI 助手，通过调用工具获取信息后再为用户解答。

可用工具：
{tools_desc}

请严格按照以下格式逐步推理（每次只调用一个工具）：

Thought: 分析问题，决定下一步行动
Action: 工具名称（必须是可用工具之一）
Action Input: 传给工具的查询内容

获得工具结果（Observation）后继续推理，直到有足够信息时输出：

Thought: 已获得足够信息
Final Answer: 你的最终回答

规则：
1. 纯闲聊可直接输出 Thought + Final Answer，无需调用工具
2. 工具名称必须与可用工具列表完全一致
3. Final Answer 必须基于工具返回的真实内容，不可编造
4. 每次只能输出一个 Action，等待 Observation 后再继续
"""


def _build_tools_desc(tools: List[Any]) -> str:
    """把工具列表格式化为提示词中的工具描述段落。"""
    return "\n".join(f"- {t.name}: {t.description}" for t in tools)


def _parse_react_output(text: str) -> Dict[str, str]:
    """
    解析 LLM 的 ReAct 格式输出。

    返回结构：
    - {"type": "final",  "content": "<最终答案>"}
    - {"type": "action", "tool": "<工具名>", "input": "<查询>"}
    - {"type": "raw",    "content": "<原始文本>"}  # 无法识别格式时的兜底
    """
    # 优先匹配 Final Answer（贪婪捕获到末尾）
    final_match = re.search(r"Final Answer[：:]\s*([\s\S]+)", text, re.IGNORECASE)
    if final_match:
        return {"type": "final", "content": final_match.group(1).strip()}

    # 匹配 Action + Action Input
    action_match = re.search(r"Action[：:]\s*(.+?)(?:\n|$)", text, re.IGNORECASE)
    input_match = re.search(
        r"Action Input[：:]\s*(.+?)(?=\n\s*(?:Thought|Action|Observation|Final Answer)[：:]|\Z)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if not input_match:
        # 降级：匹配到行尾
        input_match = re.search(r"Action Input[：:]\s*(.+?)(?:\n|$)", text, re.IGNORECASE)

    if action_match and input_match:
        return {
            "type": "action",
            "tool": action_match.group(1).strip(),
            "input": input_match.group(1).strip(),
        }

    # 文本非空则视为原始回答
    cleaned = text.strip()
    return {"type": "raw", "content": cleaned}


def _build_source_tag(used_tools: Set[str]) -> str:
    """根据已使用工具集合生成 source 字段，便于前端与日志追踪。"""
    has_rag = "search_internal_knowledge" in used_tools
    has_web = "search_web_knowledge" in used_tools
    if has_rag and has_web:
        return "ReAct Agent (RAG+互联网搜索)"
    if has_rag:
        return "ReAct Agent (RAG+MySQL回查)"
    if has_web:
        return "ReAct Agent (互联网搜索 Tavily)"
    return "ReAct Agent (AI闲聊)"


def run_react_agent(
    llm: Any,
    tools: List[Any],
    question: str,
    max_iterations: int = MAX_ITERATIONS,
) -> Dict[str, str]:
    """
    执行 ReAct Agent 主循环。

    参数：
    - llm: 已初始化的 LLM 实例（需支持 .invoke(messages) 接口）
    - tools: 工具列表，每个工具需有 .name、.description、.run(str)->str
    - question: 用户问题
    - max_iterations: 最大迭代次数（超出后强制阻断，防止 token 失控）

    返回：
    - {"reply": "...", "source": "..."}
    """
    tool_map = {t.name: t for t in tools}
    tools_desc = _build_tools_desc(tools)
    system_prompt = _REACT_SYSTEM_TEMPLATE.format(tools_desc=tools_desc)

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=question),
    ]
    used_tools: Set[str] = set()

    for iteration in range(1, max_iterations + 1):
        logger.debug("ReAct 迭代 iteration={}/{} question={}", iteration, max_iterations, question[:50])

        try:
            response = llm.invoke(messages)
            output_text = (response.content or "").strip()
        except Exception as exc:
            logger.error("LLM 调用失败 iteration={} error={}", iteration, str(exc))
            return {
                "reply": f"AI 服务暂时不可用，请稍后重试。（错误：{str(exc)}）",
                "source": "agent_error",
            }

        parsed = _parse_react_output(output_text)

        if parsed["type"] in ("final", "raw"):
            reply = parsed["content"] or "我没有找到足够的信息来回答您的问题。"
            source = _build_source_tag(used_tools)
            logger.info(
                "ReAct 完成 iterations={} source={} question={}",
                iteration,
                source,
                question[:50],
            )
            return {"reply": reply, "source": source}

        # 处理工具调用
        tool_name = parsed["tool"]
        tool_input = parsed["input"]

        if tool_name not in tool_map:
            logger.warning("Agent 请求了未知工具 tool={} iteration={}", tool_name, iteration)
            observation = (
                f"工具 '{tool_name}' 不存在，"
                f"可用工具：{', '.join(tool_map.keys())}"
            )
        else:
            logger.info("调用工具 tool={} input={}", tool_name, tool_input[:60])
            observation = tool_map[tool_name].run(tool_input)
            used_tools.add(tool_name)

        # 把本轮输出与 Observation 追加到对话历史，进入下一轮
        messages.append(AIMessage(content=output_text))
        messages.append(HumanMessage(content=f"Observation: {observation}"))

    # -------------------------------------------------------
    # 超出最大迭代次数，强制阻断
    # -------------------------------------------------------
    logger.warning(
        "ReAct 超过最大迭代次数 max_iterations={} question={}",
        max_iterations,
        question[:50],
    )
    return {
        "reply": "抱歉，我在尝试多次检索后仍无法给出完整回答，请换个方式提问。",
        "source": "agent_max_iterations_exceeded",
    }
