"""
AI 路由模块（ReAct Agent 版）。

重构说明：
- 旧的"工具路由 + 意图分类"链路已替换为 ReAct Agent 模式
- Agent 通过工具 description 自主决策调用哪个工具，执行 ReAct 循环
- 工具定义见 ai_tools.py，Agent 运行时见 ai_agent.py
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

from ai_agent import run_react_agent
from ai_tools import build_all_tools
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
    """核心对话接口（ReAct Agent 版，保持与前端兼容）。"""
    question = request.message.strip()
    if not question:
        raise HTTPException(status_code=400, detail="message 不能为空。")

    _ensure_llm_ready()
    current_time = datetime.now().strftime("%Y年%m月%d日 %A")

    try:
        tools = build_all_tools(
            session=session,
            tavily_client=tavily_client,
            current_time=current_time,
        )
        result = run_react_agent(llm=chat_llm, tools=tools, question=question)
        logger.info("ReAct Agent 完成 source={} question={}", result.get("source"), question[:50])
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
