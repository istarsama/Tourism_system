from typing import Dict, Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field

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
    spot_id: int                                # 写的是哪个景点
    
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