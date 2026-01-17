import heapq

def dijkstra_search(graph, start_id, end_id, criterion='dist'):
    """
    Dijkstra 最短路径算法
    :param graph: CampusGraph 对象
    :param start_id: 起点ID
    :param end_id: 终点ID
    :param criterion: 'dist' (最短距离) 或 'time' (最短时间/拥挤度加权)
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
        if current_node in graph.adj:
            for road in graph.adj[current_node]:
                neighbor = road.v
                
                # 根据策略决定权重
                if criterion == 'time':
                    # 假设：拥挤度 > 1 代表拥堵，时间变长
                    # 这里简单的模型：权重 = 距离 * 拥挤度
                    weight = road.distance * road.crowding
                else:
                    # 默认只看物理距离
                    weight = road.distance 
                
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