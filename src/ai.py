"""
AI 路由模块（LangGraph 多智能体版）。

重构说明：
- 旧的单体 ReAct 循环已替换为 LangGraph 多智能体架构
- 意图路由智能体 → RAG 专家 / Web 专家 / 直接闲聊，单次请求只走一条路径
- 工具层改为 LangChain 原生 @tool，支持 .bind_tools() 原生 JSON Schema 工具调用
- 图节点见 ai_agent.py：router_node / rag_agent_node / web_agent_node / chat_node / finalize_node
- 保持前端接口不变：POST /ai/rag_chat，返回 {"reply": ..., "source": ...}
- POST /ai/polish 日记润色接口保持原有逻辑不变
"""

import os
from datetime import datetime

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from loguru import logger
from pydantic import BaseModel
from sqlmodel import Session
from tavily import TavilyClient

from ai_agent import run_multi_agent
from ai_tools import build_rag_tool, build_web_tool
from database import get_session

load_dotenv()

router = APIRouter(prefix="/ai", tags=["AI Agent"])

# -----------------------------
# 配置区（都可通过 .env 覆盖）
# -----------------------------
OPENAI_COMPAT_API_KEY = os.getenv("OPENAI_COMPAT_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
OPENAI_COMPAT_BASE_URL = os.getenv("OPENAI_COMPAT_BASE_URL", "https://api.deepseek.com")
CHAT_MODEL = os.getenv("CHAT_MODEL", "deepseek-chat")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

tavily_client = TavilyClient(api_key=TAVILY_API_KEY) if TAVILY_API_KEY else None

chat_llm = None
if OPENAI_COMPAT_API_KEY:
    chat_llm = ChatOpenAI(
        model=CHAT_MODEL,
        api_key=OPENAI_COMPAT_API_KEY,
        base_url=OPENAI_COMPAT_BASE_URL,
        temperature=0.3,
    )
else:
    logger.warning("未配置 OPENAI_COMPAT_API_KEY（或 DEEPSEEK_API_KEY），AI 能力将不可用。")


class ChatRequest(BaseModel):
    message: str


class PolishRequest(BaseModel):
    content: str


def _ensure_llm_ready() -> None:
    if chat_llm is None:
        raise HTTPException(
            status_code=500,
            detail="未配置 AI 模型密钥，请检查 OPENAI_COMPAT_API_KEY/DEEPSEEK_API_KEY。",
        )


@router.post("/rag_chat")
async def rag_chat(request: ChatRequest, session: Session = Depends(get_session)):
    """核心对话接口（LangGraph 多智能体版，保持与前端兼容）。"""
    question = request.message.strip()
    if not question:
        raise HTTPException(status_code=400, detail="message 不能为空。")

    _ensure_llm_ready()
    current_time = datetime.now().strftime("%Y年%m月%d日 %A")

    try:
        rag_tool = build_rag_tool(session)
        web_tool = build_web_tool(tavily_client, current_time)
        result = run_multi_agent(
            llm=chat_llm,
            rag_tool=rag_tool,
            web_tool=web_tool,
            question=question,
        )
        logger.info("Multi-Agent 完成 source={} question={}", result.get("source"), question[:50])
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("rag_chat 执行失败 error={}", str(exc))
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/polish")
async def polish_diary(request: PolishRequest):
    """日记润色接口（保持原有能力不变）。"""
    _ensure_llm_ready()
    if not request.content.strip():
        raise HTTPException(status_code=400, detail="content 不能为空。")

    prompt = PromptTemplate.from_template(
        """你是一个中文文学编辑，请润色用户文本。
要求：
1) 不改变原意；
2) 语言更自然生动；
3) 避免过度夸张；
4) 仅输出润色后的正文。

原文：
{content}
"""
    )

    try:
        response = chat_llm.invoke(prompt.format(content=request.content))
        return {"polished": (response.content or "").strip()}
    except Exception as exc:
        logger.error("polish 接口失败 error={}", str(exc))
        raise HTTPException(status_code=500, detail=str(exc))
