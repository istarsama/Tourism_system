# src/models.py
class Spot:
    """景点/节点类"""
    def __init__(self, id, name, category, x, y, desc=""):
        self.id = id              # 景点唯一标识符
        self.name = name          # 景点名称
        self.category = category  # 景点类别：canteen(食堂)、building(建筑)、sight(景点)
        self.x = x                # 景点X坐标
        self.y = y                # 景点Y坐标
        self.desc = desc          # 景点描述信息
        self.score = 0.0          # 景点评分（预留功能）
        self.comments = []        # 景点评论列表（预留功能）        

    def __repr__(self):
        return f"[{self.id}] {self.name} ({self.category})"  # 对象字符串表示


class Road:
    """道路/边类"""
    def __init__(self, u, v, distance, transport_type="walk", crowding=1.0):
        self.u = u                # 道路起点景点ID
        self.v = v                # 道路终点景点ID
        self.distance = distance  # 两点间物理距离（米）
        self.type = transport_type  # 交通方式（walk步行、bus公交等）
        self.crowding = crowding  # 拥挤度系数（1.0正常，>1.0拥挤）
    
    @property
    def weight(self):
        """核心逻辑：根据拥挤度计算实际权重（时间/代价）"""
        return self.distance * self.crowding  # 实际权重 = 距离 × 拥挤度系数


class CampusGraph:
    """图结构类 - 使用邻接表存储"""
    def __init__(self):
        self.spots = {}      # 景点字典：{景点ID: Spot对象}
        self.adj = {}        # 邻接表：{景点ID: [相邻Road对象列表]}

    def add_spot(self, spot):  # 向图中添加景点
        self.spots[spot.id] = spot  # 存入spots字典
        if spot.id not in self.adj:
            self.adj[spot.id] = []  # 初始化邻接表

    def add_edge(self, u_id, v_id, distance, transport_type="walk", crowding=1.0):
        # 这是一个无向图，或者双向通行的有向图
        # PPT要求建立内部道路图 [cite: 101]
        edge1 = Road(u_id, v_id, distance, transport_type, crowding)
        edge2 = Road(v_id, u_id, distance, transport_type, crowding) # 反向边
        
        self.adj[u_id].append(edge1)  # 添加到u的邻接表
        self.adj[v_id].append(edge2)  # 添加到v的邻接表
        
    def get_spot_name(self, id):  # 根据ID获取景点名称
        return self.spots[id].name if id in self.spots else "Unknown"  # 存在则返回名称，否则返回Unknown