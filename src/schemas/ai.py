"""AI 接口相关 Pydantic 模型。"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None  # 可选会话 ID，不传则自动新建


class PolishRequest(BaseModel):
    content: str


class ChatMessageRead(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime


class ChatSessionRead(BaseModel):
    id: str
    title: str
    status: str
    summary: Optional[str]
    created_at: datetime
    last_active_at: datetime
    message_count: int


class ChatSessionCreate(BaseModel):
    title: str = "新对话"
