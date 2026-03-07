import json
from time import perf_counter
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, or_
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from loguru import logger

# 导入你自己写的工具模块
from database import get_session
from models import Diary, User, Comment, NationalSpot  # 👈 确保这里导入了 Comment 模型
from auth import get_current_user

# 创建路由器
router = APIRouter(prefix="/diaries", tags=["旅游日记"])

# ==========================================
# 数据传输模型 (Pydantic Models)
# ==========================================

# 1. 前端发送给我们的数据格式 (创建日记用)
class DiaryCreate(BaseModel):
    scope: str = "campus" # campus / national
    spot_id: Optional[int] = None          # 校园景点ID
    national_spot_id: Optional[int] = None # 全国景点ID
    title: str            # 标题
    content: str          # 内容
    # score: float = 5.0    # ❌ 禁止自评：发布时不能自己打分了，初始默认为0
    # 新增: 媒体文件链接列表 (图片或视频的URL)
    # 前端需要把图片上传到别的地方，然后把链接发给我们
    media_files: List[str] = [] 

# 🆕 新增：前端发表评论时发送的数据格式
class CommentCreate(BaseModel):
    diary_id: int   # 评论哪篇日记
    content: str    # 评论内容
    score: float    # 用户打的分数 (1.0 - 5.0)

# 🆕 新增：返回给前端看的评论格式
class CommentRead(BaseModel):
    user_name: str  # 评论者名字
    content: str    # 评论内容
    score: float    # 打分
    created_at: datetime # 评论时间

# 2. 我们返回给前端的数据格式 (显示日记用)
class DiaryRead(BaseModel):
    id: int
    spot_id: Optional[int]
    scope: str
    national_spot_id: Optional[int]
    user_name: str        # 作者名字
    title: str
    content: str
    score: float          # 当前平均评分
    view_count: int       # 浏览量
    media_files: List[str]# 图片列表 (我们会把字符串还原回列表发给前端)
    created_at: datetime


def _build_diary_read(session: Session, diary: Diary) -> DiaryRead:
    user = session.get(User, diary.user_id)
    user_name = user.username if user else "未知用户"
    return DiaryRead(
        id=diary.id,
        spot_id=diary.spot_id,
        scope=diary.scope,
        national_spot_id=diary.national_spot_id,
        user_name=user_name,
        title=diary.title,
        content=diary.content,
        score=diary.score,
        view_count=diary.view_count,
        media_files=json.loads(diary.media_json) if diary.media_json else [],
        created_at=diary.created_at,
    )

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
    注意：新发布的日记评分为 0，等待其他用户打分。
    """
    
    if diary_data.scope not in {"campus", "national"}:
        raise HTTPException(status_code=400, detail="scope 仅支持 'campus' 或 'national'")

    if diary_data.scope == "campus":
        if diary_data.spot_id is None:
            raise HTTPException(status_code=400, detail="campus 日记必须提供 spot_id")
        spot_id = diary_data.spot_id
        national_spot_id = None
    else:
        if diary_data.national_spot_id is None:
            raise HTTPException(status_code=400, detail="national 日记必须提供 national_spot_id")
        national_spot = session.get(NationalSpot, diary_data.national_spot_id)
        if not national_spot or not national_spot.is_active:
            raise HTTPException(status_code=404, detail="national_spot_id 对应景点不存在")
        spot_id = None
        national_spot_id = diary_data.national_spot_id

    # 1. 把前端传来的图片列表 (List) 转成 字符串 (String)
    # 例如: ['a.jpg', 'b.jpg'] -> '["a.jpg", "b.jpg"]'
    media_json_str = json.dumps(diary_data.media_files)
    
    # 2. 创建数据库对象
    new_diary = Diary(
        user_id=current_user.id,        # 自动填入当前登录用户的ID
        spot_id=spot_id,
        scope=diary_data.scope,
        national_spot_id=national_spot_id,
        title=diary_data.title,
        content=diary_data.content,
        score=0.0,                      # 👈 初始评分设为 0.0
        media_json=media_json_str,      # 存入转换后的字符串
        view_count=0                    # 刚发布，浏览量为0
    )
    
    # 3. 存入数据库
    session.add(new_diary)
    session.commit()
    session.refresh(new_diary)
    
    # 4. 返回结果给前端
    return _build_diary_read(session, new_diary)

# 🆕 【新增接口】发表评论并更新评分 (核心逻辑)
@router.post("/comment")
def add_comment(
    comment_data: CommentCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user) # 必须登录才能评论
):
    """
    【发表评论接口】
    功能：
    1. 保存用户的评论和打分。
    2. 触发【自动评分算法】：重新计算该日记的平均分。
    """
    # 1. 检查日记是否存在
    diary = session.get(Diary, comment_data.diary_id)
    if not diary:
        raise HTTPException(status_code=404, detail="日记不存在")

    # 2. 保存新的评论数据到 Comment 表
    new_comment = Comment(
        user_id=current_user.id,       # 谁评的
        diary_id=comment_data.diary_id,# 评的哪篇
        content=comment_data.content,  # 内容
        score=comment_data.score       # 打分
    )
    session.add(new_comment)
    session.commit() # 先保存评论，确保数据入库
    
    # 3. 🧠【核心算法：重新计算平均分】
    # 第一步：从数据库查出这篇日记的所有评论
    comments = session.exec(select(Comment).where(Comment.diary_id == diary.id)).all()
    
    # 第二步：计算总分
    # 使用 Python 的 sum 函数，把所有评论的 score 加起来
    total_score = sum(c.score for c in comments)
    
    # 第三步：计算平均值 (总分 / 评论人数)
    if len(comments) > 0:
        new_average = total_score / len(comments)
    else:
        new_average = 0.0
        
    # 第四步：更新 Diary 表的主分数
    diary.score = round(new_average, 1) # 保留1位小数，比较美观
    session.add(diary)
    session.commit() # 保存最新的平均分
    
    return {"message": "评论成功", "new_average_score": diary.score}

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
    
    # 3. 返回数据
    return _build_diary_read(session, diary)

# 🆕 【新增接口】获取某篇日记的所有评论列表
@router.get("/{diary_id}/comments", response_model=List[CommentRead])
def get_diary_comments(diary_id: int, session: Session = Depends(get_session)):
    """
    【获取评论列表接口】
    功能：展示某篇日记下所有的用户评论。
    """
    # 从 Comment 表里查，条件是 diary_id 匹配
    comments = session.exec(select(Comment).where(Comment.diary_id == diary_id)).all()
    
    result = []
    for c in comments:
        # 查一下评论人的名字
        user = session.get(User, c.user_id)
        user_name = user.username if user else "匿名用户"
        
        # 组装返回数据
        result.append(CommentRead(
            user_name=user_name,
            content=c.content,
            score=c.score,
            created_at=c.created_at
        ))
    return result

@router.get("/spot/{spot_id}", response_model=List[DiaryRead])
def get_spot_diaries(
    spot_id: int, 
    # 👇 新增: 接收前端传来的排序指令，默认是 'latest' (最新)
    sort_by: str = Query("latest", description="排序方式: latest(最新), heat(热度), score(评分)"),
    scope: str = Query("campus", pattern="^(campus|national)$", description="查询范围"),
    session: Session = Depends(get_session)
):
    """
    获取某景点的日记列表 (支持排序)
    PPT要求：推荐算法基础要求为排序算法
    """
    started_at = perf_counter()
    # 1. 基础查询：先找到属于这个景点(spot_id)的所有日记
    if scope == "campus":
        query = select(Diary).where(Diary.scope == "campus", Diary.spot_id == spot_id)
    else:
        query = select(Diary).where(Diary.scope == "national", Diary.national_spot_id == spot_id)
    
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
    # 为了避免代码重复，你可以把这段逻辑封装成函数，但这里为了直观，我们直接写
    result = []
    for d in diaries:
        result.append(_build_diary_read(session, d))
    elapsed_ms = (perf_counter() - started_at) * 1000
    logger.info(
        "查询景点日记 scope={} spot_id={} sort_by={} count={} elapsed_ms={:.2f}",
        scope,
        spot_id,
        sort_by,
        len(result),
        elapsed_ms,
    )
    return result


@router.get("/search", response_model=List[DiaryRead])
def search_diaries(
    # 👇 接收搜索关键词 (如果不传，就是 None，代表看全站推荐)
    keyword: Optional[str] = None,
    # 接收排序方式，默认按热度(heat)推荐
    sort_by: str = Query("heat", description="排序: heat(热度)/score(评分)/latest(最新)"),
    scope: str = Query("all", pattern="^(all|campus|national)$", description="范围过滤"),
    session: Session = Depends(get_session)
):
    """
    【全站搜索与推荐接口】
    1. 如果没有关键词 -> 变成 "全站热门日记推荐"
    2. 如果有关键词   -> 变成 "日记搜索" (搜标题或内容)
    """
    # 开始构建查询：先准备查 Diary 表
    query = select(Diary)
    if scope != "all":
        query = query.where(Diary.scope == scope)
    
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
        result.append(_build_diary_read(session, d))
    return result
