from typing import Dict, Optional, List
from datetime import datetime
from uuid import uuid4
from sqlmodel import SQLModel, Field
from sqlalchemy import UniqueConstraint, Index

# ==========================================
# 景点与地图相关模型 
# ==========================================
class Spot(SQLModel):
    """
    景点/节点模型
    对应地图 JSON 中的 "spots" 列表
    """
    id: int
    name: str
    type: str = "road"  # 类别: "spot" (景点) 或 "road" (路点)
    x: float            # 地图像素 X 坐标
    y: float            # 地图像素 Y 坐标
    desc: Optional[str] = None # 介绍文本

    def __repr__(self):
        return f"[{self.id}] {self.name} ({self.type})"

class Edge(SQLModel):
    """
    道路/边模型
    对应地图 JSON 中的 "edges" 列表
    """
    u: int              # 起点ID
    v: int              # 终点ID
    distance: float     # 距离 (像素或米)
    crowding: float = 1.0 # 拥挤度

    @property
    def weight(self):
        """计算权值：距离 x 拥挤度"""
        return self.distance * self.crowding

class CampusGraph:
    """图结构类：存储所有的景点和道路"""
    def __init__(self):
        self.spots: Dict[int, Spot] = {}  # 字典存储所有景点: {ID: Spot对象}
        self.adj: Dict[int, List[Edge]] = {} # 邻接表: {ID: [Edge对象列表]}

    def add_spot(self, spot: Spot):
        """添加一个景点"""
        self.spots[spot.id] = spot
        if spot.id not in self.adj:
            self.adj[spot.id] = []

    def add_edge(self, edge: Edge):
        """添加一条路 (自动处理无向图的双向添加)"""
        # 正向路: u -> v
        self.adj[edge.u].append(edge)
        
        # 反向路: v -> u (创建一条新的反向边)
        reverse_edge = Edge(
            u=edge.v, 
            v=edge.u, 
            distance=edge.distance, 
            crowding=edge.crowding
        )
        
        # 确保字典里有 key
        if edge.v not in self.adj:
            self.adj[edge.v] = []
            
        self.adj[edge.v].append(reverse_edge)

    def get_spot_name(self, id):
        """辅助函数：通过ID查名字"""
        return self.spots[id].name if id in self.spots else f"未知点_{id}"
# ==========================================
# 数据库模型 
# ==========================================
class User(SQLModel, table=True):
    """用户表：存储账号信息"""
    id: Optional[int] = Field(default=None, primary_key=True) # 主键ID
    username: str = Field(index=True, unique=True) # 用户名，必须唯一
    password_hash: str                             # 密码（加密存储）
    created_at: datetime = Field(default_factory=datetime.now) # 注册时间

class Diary(SQLModel, table=True):
    """旅游日记表：存储用户写的游记"""
    id: Optional[int] = Field(default=None, primary_key=True) # 日记ID
    
    user_id: int = Field(foreign_key="user.id") # 作者是谁 (关联User表)
    poi_id: Optional[int] = Field(default=None, foreign_key="poi.id", index=True) # 统一地点ID（兼容新POI体系）
    spot_id: Optional[int] = Field(default=None, index=True) # 校园景点ID（campus 模式）
    scope: str = Field(default="campus", index=True) # 日记范围: campus / national
    national_spot_id: Optional[int] = Field(default=None, foreign_key="national_spot.id", index=True)
    
    title: str    # 标题
    content: str  # 正文内容
    
    # --- 新增字段 ---
    # 浏览量 (热度)，默认是 0
    view_count: int = Field(default=0) 
    
    # 媒体文件链接 (图片/视频)
    # 因为数据库很难直接存 "列表"，我们把它转成字符串存
    # 例如: '["http://img1.jpg", "http://video.mp4"]'
    media_json: str = Field(default="[]") 
    
    score: float = Field(default=5.0) # 评分
    created_at: datetime = Field(default_factory=datetime.now) # 发布时间

# ==========================================
class Comment(SQLModel, table=True):
    """
    【评论/评分表】
    存储用户对某篇日记的评价和打分
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    
    user_id: int   # 谁评的
    diary_id: int  # 评的哪篇日记
    
    content: str   # 评论内容 (比如: "写得真好！")
    score: float   # 打分 (1.0 - 5.0)
    
    created_at: datetime = Field(default_factory=datetime.now)


class POI(SQLModel, table=True):
    """
    统一地点主表：
    - 兼容校园点位（像素坐标）与校外点位（经纬度）
    - 为路线、爬虫、推荐等模块提供统一主键
    """
    __tablename__ = "poi"
    __table_args__ = (
        UniqueConstraint("source", "source_ref", name="uq_poi_source_ref"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    poi_type: str = Field(default="campus_spot", index=True)
    source: str = Field(default="campus", index=True)
    source_ref: str = Field(index=True)
    legacy_spot_id: Optional[int] = Field(default=None, index=True, unique=True)
    description: Optional[str] = None
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class POIAlias(SQLModel, table=True):
    """地点别名表：支持关键词、同义词、清洗名称映射"""
    __tablename__ = "poi_alias"
    __table_args__ = (
        UniqueConstraint("poi_id", "normalized_alias", name="uq_poi_alias_norm"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    poi_id: int = Field(foreign_key="poi.id", index=True)
    alias: str
    normalized_alias: str = Field(index=True)
    source: str = Field(default="system", index=True)
    created_at: datetime = Field(default_factory=datetime.now)


class POIGeometry(SQLModel, table=True):
    """
    地点几何表：
    - campus_pixel: 校园像素坐标
    - wgs84_point: 真实经纬度坐标
    """
    __tablename__ = "poi_geometry"
    __table_args__ = (
        UniqueConstraint("poi_id", "geometry_type", "source", name="uq_poi_geometry"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    poi_id: int = Field(foreign_key="poi.id", index=True)
    geometry_type: str = Field(default="campus_pixel", index=True)
    x_pixel: Optional[float] = None
    y_pixel: Optional[float] = None
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    srid: str = Field(default="LOCAL_PIXEL")
    source: str = Field(default="campus_map", index=True)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class RouteCache(SQLModel, table=True):
    """路线缓存表：为后续 OSM 与混合路线缓存提供统一结构"""
    __tablename__ = "route_cache"

    id: Optional[int] = Field(default=None, primary_key=True)
    cache_key: str = Field(index=True, unique=True)
    mode: str = Field(default="campus_only", index=True)
    provider: str = Field(default="campus_graph", index=True)
    source_poi_id: Optional[int] = Field(default=None, foreign_key="poi.id", index=True)
    target_poi_id: Optional[int] = Field(default=None, foreign_key="poi.id", index=True)
    distance_m: Optional[float] = None
    duration_s: Optional[float] = None
    route_json: str = Field(default="{}")
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: Optional[datetime] = Field(default=None, index=True)


class NationalSpot(SQLModel, table=True):
    """
    全国景点表：用于 OSM/全国地图模式数据源。

    这里额外保留赏花主题与小红书抓取元数据，原因有两个：
    1. 导入脚本需要在“景点落库”和“帖子抓取”之间保留稳定状态，避免抓取失败时整条景点数据丢失。
    2. 前端全国地图模式希望直接消费帖子预览，因此景点主表需要知道当前抓取是否成功、是否需要更新 Cookie。
    """
    __tablename__ = "national_spot"
    __table_args__ = (
        UniqueConstraint("name", "city", name="uq_national_spot_name_city"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    type: str = Field(default="综合景区", index=True)
    latitude: float = Field(index=True)
    longitude: float = Field(index=True)
    description: Optional[str] = None
    city: str = Field(index=True)
    province: Optional[str] = Field(default=None, index=True)
    flower_type: Optional[str] = Field(default=None, index=True)
    best_season: Optional[str] = None
    search_keywords_json: str = Field(default="[]")
    xhs_query: Optional[str] = None
    source: str = Field(default="seed", index=True)
    rating: float = Field(default=4.5)
    is_active: bool = Field(default=True, index=True)
    xhs_fetch_status: str = Field(default="pending", index=True)
    xhs_fetch_message: Optional[str] = None
    xhs_cookie_needs_refresh: bool = Field(default=False, index=True)
    xhs_note_count: int = Field(default=0)
    xhs_last_fetched_at: Optional[datetime] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class NationalSpotXHSNote(SQLModel, table=True):
    """
    全国景点关联的小红书帖子预览表。

    只存前端立即可用的预览字段，不直接保存完整抓取结果：
    - 降低接口响应体与数据库膨胀风险
    - 保持“地图点位 -> 帖子缩略图/文案/跳转链接”的最短链路
    """
    __tablename__ = "national_spot_xhs_note"
    __table_args__ = (
        UniqueConstraint("national_spot_id", "xhs_note_id", name="uq_national_spot_xhs_note"),
        Index("ix_national_spot_xhs_note_rank", "national_spot_id", "rank_order"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    national_spot_id: int = Field(foreign_key="national_spot.id", index=True)
    xhs_note_id: str = Field(index=True)
    title: str
    content_preview: str = Field(default="")
    thumbnail_url: Optional[str] = None
    xhs_url: str
    author_name: Optional[str] = None
    author_id: Optional[str] = None
    liked_count: int = Field(default=0)
    image_urls_json: str = Field(default="[]")
    rank_order: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class MapConfig(SQLModel, table=True):
    """地图配置表：支持校园/全国地图模式切换"""
    __tablename__ = "map_config"

    id: Optional[int] = Field(default=None, primary_key=True)
    scope: str = Field(index=True, unique=True)
    center_lat: Optional[float] = Field(default=None)
    center_lng: Optional[float] = Field(default=None)
    zoom_level: int = Field(default=15)
    map_provider: str = Field(default="campus_canvas")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


# ==========================================
# 会话与记忆持久化模型
# ==========================================

def _uuid_str() -> str:
    return str(uuid4())


class ChatSession(SQLModel, table=True):
    """
    聊天会话表：每个用户可以有多个独立会话。
    所有查询必须同时按 user_id + id 过滤，保证会话隔离。
    """
    __tablename__ = "chat_session"
    __table_args__ = (
        Index("ix_chat_session_user_active", "user_id", "last_active_at"),
    )

    id: str = Field(default_factory=_uuid_str, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    title: str = Field(default="新对话")
    status: str = Field(default="active", index=True)  # active / archived
    summary: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    last_active_at: datetime = Field(default_factory=datetime.now)


class ChatMessage(SQLModel, table=True):
    """
    聊天消息表：存储会话中的每一轮对话。
    按 session_id + created_at 排序即可重放完整对话。
    """
    __tablename__ = "chat_message"
    __table_args__ = (
        Index("ix_chat_message_session_time", "session_id", "created_at"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(foreign_key="chat_session.id", index=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    role: str = Field(index=True)       # user / assistant / system / tool
    content: str
    metadata_json: str = Field(default="{}")  # 工具调用结果、来源标记等
    created_at: datetime = Field(default_factory=datetime.now)


class MemoryItem(SQLModel, table=True):
    """
    记忆条目表：存储从对话中提取的持久化记忆。
    - session 级记忆：绑定到特定会话，会话归档后可清理
    - user 级记忆：跨会话持久，如用户偏好、历史摘要
    """
    __tablename__ = "memory_item"
    __table_args__ = (
        Index("ix_memory_user_scope", "user_id", "memory_scope"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    session_id: Optional[str] = Field(default=None, foreign_key="chat_session.id", index=True)
    memory_scope: str = Field(default="session", index=True)  # session / user / system
    content: str
    source: str = Field(default="auto")      # auto / manual / summary
    importance: float = Field(default=0.5)   # 0.0 ~ 1.0
    expires_at: Optional[datetime] = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
