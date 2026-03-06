from typing import Dict, Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field
from sqlalchemy import UniqueConstraint

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
    """全国景点表：用于 OSM/全国地图模式数据源"""
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
    rating: float = Field(default=4.5)
    is_active: bool = Field(default=True, index=True)
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
