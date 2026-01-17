# src/models.py
class Spot:
    """景点/节点类"""
    def __init__(self, id, name, category, x, y, desc=""):
        self.id = id              
        self.name = name          
        self.category = category  # 类别：canteen, building, sight
        self.x = x                
        self.y = y                
        self.desc = desc          
        # 预留给后续功能：评分和评论
        self.score = 0.0          
        self.comments = []        

    def __repr__(self):
        return f"[{self.id}] {self.name} ({self.category})"


class Road:
    """道路/边类"""
    def __init__(self, u, v, distance, transport_type="walk", crowding=1.0):
        self.u = u                # 起点ID
        self.v = v                # 终点ID
        self.distance = distance  # 物理距离
        self.type = transport_type 
        self.crowding = crowding  # 拥挤度系数
    
    @property
    def weight(self):
        """核心逻辑：根据拥挤度计算实际权重（时间/代价）"""
        return self.distance * self.crowding


class CampusGraph:
    """图结构类 - 使用邻接表存储"""
    def __init__(self):
        self.spots = {}      # {id: Spot对象}
        self.adj = {}        # {id: [Road对象, ...]} 邻接表

    def add_spot(self, spot):
        self.spots[spot.id] = spot
        if spot.id not in self.adj:
            self.adj[spot.id] = []

    def add_edge(self, u_id, v_id, distance, transport_type="walk", crowding=1.0):
        # 这是一个无向图，或者双向通行的有向图
        # PPT要求建立内部道路图 [cite: 101]
        edge1 = Road(u_id, v_id, distance, transport_type, crowding)
        edge2 = Road(v_id, u_id, distance, transport_type, crowding) # 反向边
        
        self.adj[u_id].append(edge1)
        self.adj[v_id].append(edge2)
        
    def get_spot_name(self, id):
        return self.spots[id].name if id in self.spots else "Unknown"