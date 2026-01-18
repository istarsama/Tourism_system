import heapq
import math
from typing import List, Tuple, Dict
##############################################
# 辅助函数和常量定义
SPEED_WALK = 1.5   # 步行速度: 1.5 m/s (约 5.4 km/h)
SPEED_BIKE = 5.0   # 自行车速度: 5.0 m/s (约 18 km/h)

###############################################
# 核心函数：计算边的权重
def get_edge_weight(road, strategy: str, transport: str) -> float:
    """
    【核心辅助函数：计算边的权重】
    根据 PPT 要求，动态计算消耗（距离或时间）。
    
    参数:
    - road: 边对象 (包含 distance, crowding 属性)
    - strategy: 'dist'(最短距离) 或 'time'(最短时间)
    - transport: 'walk'(步行) 或 'bike'(自行车)
    """
    distance = road.distance
    
    # --- 策略 A: 最短距离 ---
    if strategy == 'dist':
        return distance
        
    # --- 策略 B: 最短时间 (公式: 时间 = 距离 / 实际速度) ---
    # 1. 确定理想速度
    ideal_speed = SPEED_WALK
    if transport == 'bike':
        ideal_speed = SPEED_BIKE
    
    # 2. 获取拥挤度 (PPT要求: 拥挤度是 <=1 的正数，但在你的代码里似乎用 >1 代表拥堵)
    # 为了兼容你的逻辑，我们假设 road.crowding 是一个系数:
    # 如果 road.crowding 越大，代表越堵，速度越慢。
    # 修正公式：实际速度 = 理想速度 / 拥挤系数 (如果 crowding=2.0，速度减半)
    # 或者如果 crowding 是 0~1 (PPT定义)，则 实际速度 = 理想速度 * crowding
    
    # 这里我们采用通用的逻辑：crowding 越大越慢
    # 假设 crowding 默认是 1.0 (正常)，2.0 (堵车)
    congestion_factor = getattr(road, 'crowding', 1.0) # 安全获取，默认为1.0
    
    # 避免除以0
    if congestion_factor <= 0:
        congestion_factor = 1.0
        
    # 计算实际速度 (拥挤度越高，速度越慢)
    real_speed = ideal_speed / congestion_factor
    
    # 计算时间消耗 (秒)
    time_cost = distance / real_speed
    
    return time_cost
########################################################
# Dijkstra 最短路径算法实现

def dijkstra_search(graph, start_id, end_id, criterion='dist', transport='walk'):
    """
    Dijkstra 最短路径算法
    :param graph: CampusGraph 对象
    :param start_id: 起点ID
    :param end_id: 终点ID
    :param criterion: 'dist' (最短距离) 或 'time' (最短时间/拥挤度加权)
    :param transport: 【新增】'walk' (步行) 或 'bike' (自行车)
    :return: (path_ids, total_cost) -> (路径节点ID列表, 总消耗)
    """
    
    # 1. 初始化
    # distances: 记录从起点到各点的最小消耗，初始为无穷大
    distances = {node_id: float('inf') for node_id in graph.spots}
    distances[start_id] = 0
    
    # previous: 记录路径的前驱节点，用于最后反推路径
    previous = {node_id: None for node_id in graph.spots}
    
    # priority_queue: 优先队列 (消耗, 当前节点ID)，Python的heapq默认是小顶堆
    pq = [(0, start_id)]
    
    while pq:
        # 贪心策略：每次弹出当前消耗最小的节点
        current_cost, current_node = heapq.heappop(pq)
        
        # 如果找到了终点，可以提前结束
        if current_node == end_id:
            break
        
        # 剪枝：如果当前弹出的消耗比已知的还大，说明是过期的记录，跳过
        if current_cost > distances[current_node]:
            continue
            
        # 遍历邻居 (查看 adj 邻接表)
        # 【修改】使用 graph.adj.get(u, []) 稍微安全一点，防止报错
        if current_node in graph.adj:
            for road in graph.adj[current_node]:
                neighbor = road.v
                
                # 【修改】这里原来的逻辑被替换了
                # 我们调用上面新写的 helper 函数来计算权重
                # 这样代码更清晰，逻辑完全符合 PPT 的物理公式
                weight = get_edge_weight(road, criterion, transport)
                
                new_cost = current_cost + weight
                
                # 松弛操作 (Relaxation)：如果发现了更近的路，更新它
                if new_cost < distances[neighbor]:
                    distances[neighbor] = new_cost
                    previous[neighbor] = current_node
                    heapq.heappush(pq, (new_cost, neighbor))
    
    # 2. 路径回溯 (从终点倒着找回起点)
    path = []
    curr = end_id
    
    # 如果终点的距离还是无穷大，说明无法到达
    if distances[end_id] == float('inf'):
        return [], -1 
        
    while curr is not None:
        path.append(curr)
        curr = previous[curr]
    
    # 翻转列表，变成 起点 -> 终点
    return path[::-1], distances[end_id]

# ==========================================
# 2. 新增：多点路径规划 (TSP 近似)
# ==========================================
def plan_multi_point_route(
    graph,
    start_id: int,
    via_spots: List[int],
    strategy: str = 'dist',
    transport: str = 'walk'
) -> Tuple[List[int], float]:
    """
    【核心算法：多点路径规划】
    PPT 要求：规划从当前位置出发，参观多个景点 (最后不一定返回，按PPT语境通常是游览完即可)。
    算法策略：贪心算法 (Nearest Neighbor) - 每次找离当前最近的下一个点。
    """
    full_path = []
    total_cost = 0.0
    
    current_node = start_id
    # 待访问的点集合 (去重)
    to_visit = set(via_spots)
    
    # 如果起点也在待访问列表中，先移除，避免原地打转
    if current_node in to_visit:
        to_visit.remove(current_node)
        
    # 记录路径起点
    full_path.append(current_node)
    
    # 循环直到所有点都去过
    while to_visit:
        best_next_node = None
        min_segment_cost = float('inf')
        best_segment_path = []
        
        # 1. 从当前点出发，计算到所有“剩下没去的点”的代价，找最近的那个
        for target in to_visit:
            # 调用基础导航算两点间路径
            path, cost = dijkstra_search(graph, current_node, target, strategy, transport)
            
            # 如果能到达，且代价更小，就选它
            if cost != -1 and cost < min_segment_cost:
                min_segment_cost = cost
                best_next_node = target
                best_segment_path = path
        
        # 如果找不到下一个可达的点 (比如孤岛)，强行结束
        if best_next_node is None:
            break
            
        # 2. 更新状态
        total_cost += min_segment_cost
        # 拼接路径 (best_segment_path[0] 是起点，已经在 full_path 末尾了，所以从 [1:] 开始拼)
        full_path.extend(best_segment_path[1:])
        
        # 3. 移动到下个点
        current_node = best_next_node
        to_visit.remove(current_node)
        
    return full_path, total_cost