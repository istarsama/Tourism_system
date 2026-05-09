"""
AI 会话服务层：管理 ChatSession / ChatMessage / MemoryItem 的持久化。

职责：
- 创建或获取会话
- 追加消息
- 首轮完成后调用 LLM 为会话生成摘要式标题
- 更新会话最后活跃时间
"""

from datetime import datetime
from typing import Any, Optional

from sqlmodel import Session, select
from loguru import logger

from models import ChatSession, ChatMessage, User


def get_or_create_session(
    db: Session,
    user: User,
    session_id: Optional[str] = None,
) -> ChatSession:
    """
    如果 session_id 存在且属于该用户，则返回已有会话；
    否则创建新会话。
    """
    if session_id:
        chat_session = db.exec(
            select(ChatSession).where(
                ChatSession.id == session_id,
                ChatSession.user_id == user.id,
                ChatSession.status == "active",
            )
        ).first()
        if chat_session:
            return chat_session
        logger.warning(
            "session_id={} 不属于用户 {} 或已归档，将新建会话",
            session_id,
            user.id,
        )

    chat_session = ChatSession(
        user_id=user.id,
        title="新对话",
        status="active",
    )
    db.add(chat_session)
    db.commit()
    db.refresh(chat_session)
    return chat_session


def append_message(
    db: Session,
    session: ChatSession,
    user: User,
    role: str,
    content: str,
    metadata: Optional[dict] = None,
) -> ChatMessage:
    """追加一条消息并更新会话的最后活跃时间。"""
    import json

    msg = ChatMessage(
        session_id=session.id,
        user_id=user.id,
        role=role,
        content=content,
        metadata_json=json.dumps(metadata or {}, ensure_ascii=False),
    )
    db.add(msg)

    session.last_active_at = datetime.now()
    db.add(session)

    db.commit()
    db.refresh(msg)
    return msg


def generate_session_title(
    db: Session,
    session: ChatSession,
    llm: Any,
    question: str,
    answer: str,
) -> None:
    """
    在首轮对话结束后（标题仍为"新对话"），调用 LLM 生成简短摘要式标题，
    并将其回写到会话记录中。
    生成失败时静默降级，不影响主流程。
    """
    if session.title != "新对话":
        return
    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        resp = llm.invoke(
            [
                SystemMessage(
                    content=(
                        "根据下面的用户提问和 AI 回答，用不超过 15 个中文字生成一个简短的对话标题。"
                        "只输出标题本身，不加任何标点或解释。"
                    )
                ),
                HumanMessage(
                    content=f"用户提问：{question}\nAI 回答：{answer[:200]}"
                ),
            ]
        )
        title = (resp.content or "").strip()[:30] or "新对话"
    except Exception as exc:
        logger.warning("生成会话标题失败（降级为默认）: {}", exc)
        title = question[:20].strip() or "新对话"

    session.title = title
    db.add(session)
    db.commit()


def archive_session(db: Session, session: ChatSession) -> None:
    """将会话标记为已归档。"""
    session.status = "archived"
    db.add(session)
    db.commit()
