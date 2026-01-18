import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, or_
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# 导入你自己写的工具模块
from database import get_session
from models import Diary, User
from auth import get_current_user

# 创建路由器
router = APIRouter(prefix="/diaries", tags=["旅游日记"])

# ==========================================
# 数据传输模型 (Pydantic Models)
# ==========================================

# 1. 前端发送给我们的数据格式 (创建日记用)
class DiaryCreate(BaseModel):
    spot_id: int          # 景点ID
    title: str            # 标题
    content: str          # 内容
    score: float = 5.0    # 评分
    # 新增: 媒体文件链接列表 (图片或视频的URL)
    # 前端需要把图片上传到别的地方，然后把链接发给我们
    media_files: List[str] = [] 

# 2. 我们返回给前端的数据格式 (显示日记用)
class DiaryRead(BaseModel):
    id: int
    spot_id: int
    user_name: str        # 作者名字
    title: str
    content: str
    score: float
    view_count: int       # 浏览量
    media_files: List[str]# 图片列表 (我们会把字符串还原回列表发给前端)
    created_at: datetime

# ==========================================
# 接口逻辑
# ==========================================

@router.post("/", response_model=DiaryRead)
def create_diary(
    diary_data: DiaryCreate, 
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user) # 必须登录才能写
):
    """
    【发布日记接口】
    功能：保存用户提交的日记，包括图片链接。
    """
    
    # 1. 把前端传来的图片列表 (List) 转成 字符串 (String)
    # 例如: ['a.jpg', 'b.jpg'] -> '["a.jpg", "b.jpg"]'
    media_json_str = json.dumps(diary_data.media_files)
    
    # 2. 创建数据库对象
    new_diary = Diary(
        user_id=current_user.id,        # 自动填入当前登录用户的ID
        spot_id=diary_data.spot_id,
        title=diary_data.title,
        content=diary_data.content,
        score=diary_data.score,
        media_json=media_json_str,      # 存入转换后的字符串
        view_count=0                    # 刚发布，浏览量为0
    )
    
    # 3. 存入数据库
    session.add(new_diary)
    session.commit()
    session.refresh(new_diary)
    
    # 4. 返回结果给前端
    return DiaryRead(
        id=new_diary.id,
        spot_id=new_diary.spot_id,
        user_name=current_user.username,
        title=new_diary.title,
        content=new_diary.content,
        score=new_diary.score,
        view_count=new_diary.view_count,
        # 把字符串再转回列表，方便前端直接使用
        media_files=json.loads(new_diary.media_json), 
        created_at=new_diary.created_at
    )


@router.get("/detail/{diary_id}", response_model=DiaryRead)
def get_diary_detail(diary_id: int, session: Session = Depends(get_session)):
    """
    【查看日记详情接口】 (重要功能)
    功能：获取某篇日记的详细内容，并且让 浏览量(热度) +1
    PPT要求: "旅游日记的浏览量即为该日记的热度"
    """
    
    # 1. 查数据库找日记
    diary = session.get(Diary, diary_id)
    if not diary:
        raise HTTPException(status_code=404, detail="日记不存在")
    
    # 2. 核心逻辑：浏览量 +1
    diary.view_count += 1
    session.add(diary)     # 标记为更新
    session.commit()       # 提交保存
    session.refresh(diary) # 刷新数据
    
    # 3. 查作者名字 (用来显示是谁写的)
    user = session.get(User, diary.user_id)
    user_name = user.username if user else "未知用户"
    
    # 4. 返回数据
    return DiaryRead(
        id=diary.id,
        spot_id=diary.spot_id,
        user_name=user_name,
        title=diary.title,
        content=diary.content,
        score=diary.score,
        view_count=diary.view_count,
        # 解析媒体文件 JSON 字符串 -> List
        media_files=json.loads(diary.media_json) if diary.media_json else [],
        created_at=diary.created_at
    )

#######################################
# 🔄 替换整个 get_spot_diaries 函数
@router.get("/spot/{spot_id}", response_model=List[DiaryRead])
def get_spot_diaries(
    spot_id: int, 
    # 👇 新增: 接收前端传来的排序指令，默认是 'latest' (最新)
    sort_by: str = Query("latest", description="排序方式: latest(最新), heat(热度), score(评分)"),
    session: Session = Depends(get_session)
):
    """
    获取某景点的日记列表 (支持排序)
    PPT要求：推荐算法基础要求为排序算法
    """
    # 1. 基础查询：先找到属于这个景点(spot_id)的所有日记
    query = select(Diary).where(Diary.spot_id == spot_id)
    
    # 2. 🧠 核心算法：根据 sort_by 参数决定怎么排
    if sort_by == "heat":
        # 按浏览量(view_count) 从大到小(desc) 排
        query = query.order_by(Diary.view_count.desc())
    elif sort_by == "score":
        # 按评分(score) 从高到低(desc) 排
        query = query.order_by(Diary.score.desc())
    else:
        # 默认情况：按创建时间(created_at) 从新到旧 排
        query = query.order_by(Diary.created_at.desc())
        
    # 3. 执行查询，拿到数据
    diaries = session.exec(query).all()
    
    # 4. 组装数据返回给前端 (把 JSON 字符串还原成列表)
    result = []
    for d in diaries:
        # 顺便查一下作者名字
        user = session.get(User, d.user_id)
        user_name = user.username if user else "未知用户"
        
        result.append(DiaryRead(
            id=d.id,
            spot_id=d.spot_id,
            user_name=user_name,
            title=d.title,
            content=d.content,
            score=d.score,
            view_count=d.view_count,
            # 如果有媒体文件就解析，没有就是空列表
            media_files=json.loads(d.media_json) if d.media_json else [],
            created_at=d.created_at
        ))
        
    return result


# ➕ 把这段代码加到文件最后面

@router.get("/search", response_model=List[DiaryRead])
def search_diaries(
    # 👇 接收搜索关键词 (如果不传，就是 None，代表看全站推荐)
    keyword: Optional[str] = None,
    # 接收排序方式，默认按热度(heat)推荐
    sort_by: str = Query("heat", description="排序: heat(热度)/score(评分)/latest(最新)"),
    session: Session = Depends(get_session)
):
    """
    【全站搜索与推荐接口】
    1. 如果没有关键词 -> 变成 "全站热门日记推荐"
    2. 如果有关键词   -> 变成 "日记搜索" (搜标题或内容)
    """
    # 开始构建查询：先准备查 Diary 表
    query = select(Diary)
    
    # 🕵️ 搜索逻辑 (核心算法: 模糊查询)
    if keyword:
        # where (标题包含关键词 OR 内容包含关键词)
        # Diary.title.contains(keyword) 就是 SQL 里的 LIKE %keyword%
        query = query.where(or_(Diary.title.contains(keyword), Diary.content.contains(keyword)))
    
    # 📊 排序逻辑 (核心算法: 排序)
    if sort_by == "heat":
        query = query.order_by(Diary.view_count.desc()) # 最热的在前面
    elif sort_by == "score":
        query = query.order_by(Diary.score.desc())      # 分最高的在前面
    else:
        query = query.order_by(Diary.created_at.desc()) # 最新的在前面
        
    # 执行查询
    diaries = session.exec(query).all()
    
    # 组装返回结果
    result = []
    for d in diaries:
        user = session.get(User, d.user_id)
        user_name = user.username if user else "未知用户"
        result.append(DiaryRead(
            id=d.id, spot_id=d.spot_id, user_name=user_name,
            title=d.title, content=d.content, score=d.score, view_count=d.view_count,
            media_files=json.loads(d.media_json) if d.media_json else [],
            created_at=d.created_at
        ))
    return result