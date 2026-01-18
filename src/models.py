from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field

# ==========================================
# 景点与地图相关模型 
# ==========================================
class Spot:
    """景点/节点类：表示地图上的一个点（如食堂、教学楼）"""
    def __init__(self, id, name, category, x, y, desc=""):
        self.id = id              # 景点唯一ID (例如: 1)
        self.name = name          # 景点名称 (例如: "北邮西门")
        self.category = category  # 类别 (例如: "sight" 景点, "canteen" 食堂)
        self.x = x                # 地图上的横坐标
        self.y = y                # 地图上的纵坐标
        self.desc = desc          # 景点介绍文本

    def __repr__(self):
        # 打印对象时显示的信息，方便调试
        return f"[{self.id}] {self.name} ({self.category})"


class Road:
    """道路/边类：表示连接两个景点的路"""
    def __init__(self, u, v, distance, transport_type="walk", crowding=1.0):
        self.u = u                # 起点ID
        self.v = v                # 终点ID
        self.distance = distance  # 距离（米）
        self.type = transport_type  # 交通方式 (walk/bus/bike)
        self.crowding = crowding  # 拥挤度 (1.0是正常，数值越大越堵)
    
    @property
    def weight(self):
        """计算权值：距离 x 拥挤度 = 实际花费的代价"""
        return self.distance * self.crowding


class CampusGraph:
    """图结构类：存储所有的景点和道路"""
    def __init__(self):
        self.spots = {}      # 字典存储所有景点: {ID: Spot对象}
        self.adj = {}        # 邻接表存储所有路: {ID: [Road对象列表]}

    def add_spot(self, spot):
        """添加一个景点"""
        self.spots[spot.id] = spot
        if spot.id not in self.adj:
            self.adj[spot.id] = []  # 初始化该景点的道路列表

    def add_edge(self, u_id, v_id, distance, transport_type="walk", crowding=1.0):
        """添加一条路 (双向通行)"""
        # 正向路: u -> v
        edge1 = Road(u_id, v_id, distance, transport_type, crowding)
        # 反向路: v -> u
        edge2 = Road(v_id, u_id, distance, transport_type, crowding) 
        
        self.adj[u_id].append(edge1)
        self.adj[v_id].append(edge2)
        
    def get_spot_name(self, id):
        """辅助函数：通过ID查名字"""
        return self.spots[id].name if id in self.spots else "未知地点"


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