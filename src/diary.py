# src/diary.py
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from pydantic import BaseModel
from typing import List
from datetime import datetime

from database import get_session
from models import Diary, User
from auth import get_current_user # 导入刚才写的“验票员”

router = APIRouter(prefix="/diaries", tags=["旅游日记"])

# --- 数据模型 (前端发过来的格式) ---
class DiaryCreate(BaseModel):
    spot_id: int
    title: str
    content: str
    score: float = 5.0

class DiaryRead(BaseModel):
    id: int
    spot_id: int
    user_name: str # 我们返回用户名，而不是冰冷的 user_id
    title: str
    content: str
    score: float
    created_at: datetime

# --- 接口 ---

@router.post("/", response_model=DiaryRead)
def create_diary(
    diary_data: DiaryCreate, 
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user) # 🔒 关键：必须登录！
):
    """写日记 (只有登录用户能调)"""
    
    # 1. 创建数据库对象
    # 注意：user_id 是我们自动从 Token 里拿的，不是前端传的，防止冒充！
    new_diary = Diary(
        user_id=current_user.id, 
        spot_id=diary_data.spot_id,
        title=diary_data.title,
        content=diary_data.content,
        score=diary_data.score
    )
    
    session.add(new_diary)
    session.commit()
    session.refresh(new_diary)
    
    # 2. 返回给前端的数据
    return DiaryRead(
        id=new_diary.id,
        spot_id=new_diary.spot_id,
        user_name=current_user.username,
        title=new_diary.title,
        content=new_diary.content,
        score=new_diary.score,
        created_at=new_diary.created_at
    )

@router.get("/{spot_id}", response_model=List[DiaryRead])
def get_spot_diaries(spot_id: int, session: Session = Depends(get_session)):
    """获取某个景点的所有日记 (所有人都能看，不需要登录)"""
    
    # 1. 查数据库
    statement = select(Diary).where(Diary.spot_id == spot_id).order_by(Diary.created_at.desc())
    diaries = session.exec(statement).all()
    
    # 2. 组装数据 (需要多查一次 User 表获取用户名，或者用 SQL Join，这里简单处理)
    result = []
    for d in diaries:
        # 简单粗暴：根据 id 查用户名 (虽然效率低，但课设足够了)
        user = session.get(User, d.user_id)
        user_name = user.username if user else "未知用户"
        
        result.append(DiaryRead(
            id=d.id,
            spot_id=d.spot_id,
            user_name=user_name,
            title=d.title,
            content=d.content,
            score=d.score,
            created_at=d.created_at
        ))
        
    return result