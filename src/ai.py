"""
AI 路由模块（LangGraph 多智能体版）。

重构说明：
- 旧的单体 ReAct 循环已替换为 LangGraph 多智能体架构
- 意图路由智能体 → RAG 专家 / Web 专家 / 直接闲聊，单次请求只走一条路径
- 工具层改为 LangChain 原生 @tool，支持 .bind_tools() 原生 JSON Schema 工具调用
- 图节点见 ai_agent.py：router_node / rag_agent_node / web_agent_node / chat_node / finalize_node
- 保持前端接口不变：POST /ai/rag_chat，返回 {"reply": ..., "source": ...}
- POST /ai/polish 日记润色接口保持原有逻辑不变

会话持久化（新增）：
- /ai/rag_chat 支持可选 session_id 字段，不传则为匿名模式；
  已登录用户可传 session_id，每轮问答自动写入 ChatSession / ChatMessage。
- POST /ai/sessions        创建新会话（需登录）
- GET  /ai/sessions        列出当前用户的所有活跃会话（需登录）
- GET  /ai/sessions/{id}/messages  获取会话消息列表（需登录）
- DELETE /ai/sessions/{id} 归档（软删除）会话（需登录）
"""

import os
from datetime import datetime
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from loguru import logger
from sqlmodel import Session, select
from tavily import TavilyClient

from ai_agent import run_multi_agent
from ai_tools import build_rag_tool, build_web_tool
from auth import get_current_user, SECRET_KEY, ALGORITHM
from database import get_session
from models import ChatMessage, ChatSession, User
from schemas.ai import (
    ChatMessageRead,
    ChatRequest,
    ChatSessionCreate,
    ChatSessionRead,
    PolishRequest,
)
from services.ai_session_service import (
    append_message,
    archive_session,
    generate_session_title,
    get_or_create_session,
)

load_dotenv()

router = APIRouter(prefix="/ai", tags=["AI Agent"])

# 可选 Bearer token（auto_error=False 使缺少 token 时返回 None 而非 401）
_optional_oauth2 = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)

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


def _ensure_llm_ready() -> None:
    if chat_llm is None:
        raise HTTPException(
            status_code=500,
            detail="未配置 AI 模型密钥，请检查 OPENAI_COMPAT_API_KEY/DEEPSEEK_API_KEY。",
        )


def get_optional_user(
    db: Session = Depends(get_session),
    token: Optional[str] = Depends(_optional_oauth2),
) -> Optional[User]:
    """可选鉴权依赖：有 token 时尝试解析用户，无 token 或解析失败时返回 None。"""
    if not token:
        return None
    try:
        import jwt
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            return None
        user = db.get(User, int(user_id))
        return user
    except Exception:
        return None


# ─────────────────────────────────────────────────
# 核心对话接口
# ─────────────────────────────────────────────────


@router.post("/rag_chat")
async def rag_chat(
    request: ChatRequest,
    session: Session = Depends(get_session),
    # 可选鉴权：未登录用户也可使用，只是不持久化会话
    optional_user: Optional[User] = Depends(get_optional_user),
):
    """
    核心对话接口（LangGraph 多智能体版）。

    - 匿名调用：不传 Authorization Header，对话不持久化。
    - 已登录用户：可传 session_id，每轮问答自动写入 ChatSession / ChatMessage；
      不传 session_id 则自动新建会话。
    """
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
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("rag_chat 执行失败 error={}", str(exc))
        raise HTTPException(status_code=500, detail=str(exc))

    # 会话持久化（仅在用户已登录时执行）
    response_session_id: Optional[str] = None
    if optional_user is not None:
        try:
            chat_session = get_or_create_session(
                db=session,
                user=optional_user,
                session_id=request.session_id,
            )
            append_message(session, chat_session, optional_user, "user", question)
            append_message(
                session,
                chat_session,
                optional_user,
                "assistant",
                result.get("reply", ""),
                metadata={"source": result.get("source", "")},
            )
            # 首轮结束后由 LLM 生成标题
            generate_session_title(
                db=session,
                session=chat_session,
                llm=chat_llm,
                question=question,
                answer=result.get("reply", ""),
            )
            response_session_id = chat_session.id
        except Exception as exc:
            logger.warning("会话持久化失败（不影响回答）: {}", exc)

    return {
        **result,
        "session_id": response_session_id,
    }


# ─────────────────────────────────────────────────
# 日记润色
# ─────────────────────────────────────────────────


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


# ─────────────────────────────────────────────────
# 会话管理接口
# ─────────────────────────────────────────────────


@router.post("/sessions", response_model=ChatSessionRead)
def create_session(
    body: ChatSessionCreate,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """创建新的对话会话。"""
    chat_session = ChatSession(
        user_id=current_user.id,
        title=body.title,
        status="active",
    )
    db.add(chat_session)
    db.commit()
    db.refresh(chat_session)
    return _session_to_read(db, chat_session)


@router.get("/sessions", response_model=List[ChatSessionRead])
def list_sessions(
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """列出当前用户的所有活跃会话（按最后活跃时间降序）。"""
    sessions = db.exec(
        select(ChatSession)
        .where(ChatSession.user_id == current_user.id, ChatSession.status == "active")
        .order_by(ChatSession.last_active_at.desc())
    ).all()
    return [_session_to_read(db, s) for s in sessions]


@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessageRead])
def get_session_messages(
    session_id: str,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """获取指定会话的消息列表（按时间升序）。"""
    chat_session = db.exec(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id,
        )
    ).first()
    if not chat_session:
        raise HTTPException(status_code=404, detail="会话不存在")

    messages = db.exec(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
    ).all()
    return [
        ChatMessageRead(
            id=m.id,
            role=m.role,
            content=m.content,
            created_at=m.created_at,
        )
        for m in messages
    ]


@router.delete("/sessions/{session_id}")
def delete_session(
    session_id: str,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """归档（软删除）指定会话。"""
    chat_session = db.exec(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id,
            ChatSession.status == "active",
        )
    ).first()
    if not chat_session:
        raise HTTPException(status_code=404, detail="会话不存在或已归档")

    archive_session(db, chat_session)
    return {"message": "会话已归档"}


# ─────────────────────────────────────────────────
# 内部辅助工具
# ─────────────────────────────────────────────────


def _session_to_read(db: Session, chat_session: ChatSession) -> ChatSessionRead:
    count = db.exec(
        select(ChatMessage).where(ChatMessage.session_id == chat_session.id)
    ).all()
    return ChatSessionRead(
        id=chat_session.id,
        title=chat_session.title,
        status=chat_session.status,
        summary=chat_session.summary,
        created_at=chat_session.created_at,
        last_active_at=chat_session.last_active_at,
        message_count=len(count),
    )


# ─────────────────────────────────────────────────
# 遗留：供 /plan/xhs_trip 调用的景点提取函数
# ─────────────────────────────────────────────────


async def extract_spots_from_text(text: str) -> list:
    """从文本中提取景点名称（旧版功能，保留兼容性）。"""
    if not chat_llm:
        return []
    try:
        prompt = PromptTemplate.from_template(
            "从以下旅游笔记中提取主要景点名称，以JSON列表形式输出（只输出列表，不要解释）：\n{text}"
        )
        response = chat_llm.invoke(prompt.format(text=text[:2000]))
        import json
        content = (response.content or "[]").strip()
        return json.loads(content)
    except Exception as exc:
        logger.warning("景点提取失败: {}", exc)
        return []
