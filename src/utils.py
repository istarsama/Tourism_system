import json
import os
from models import CampusGraph, Spot, Edge

def load_graph_from_json(filepath):
    """
    读取JSON文件并构建图的通用函数
    适配 v2.0/v3.0 打点工具生成的 JSON 格式
    """
    graph = CampusGraph()
    
    if not os.path.exists(filepath):
        # 如果找不到文件，打印个提示并返回空图，防止直接报错崩溃
        print(f"⚠️ 警告: 地图文件不存在: {filepath}")
        return graph

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    # 1. 加载点 (spots)
    # 注意：新工具生成的 key 是 "spots"，不是 "nodes"
    for item in data.get('spots', []):
        spot = Spot(
            id=item['id'],
            name=item['name'],
            type=item.get('type', 'road'), # 默认为 road
            x=item['x'],
            y=item['y'],
            desc=item.get('desc', "")
        )
        graph.add_spot(spot)
        
    # 2. 加载边 (edges)
    for item in data.get('edges', []):
        edge = Edge(
            u=item['u'],
            v=item['v'],
            distance=item['distance'],   # 新工具生成的 key 是 "distance"
            crowding=item.get('crowding', 1.0)
        )
        graph.add_edge(edge)
                        
    print(f"✅ 地图加载成功: {len(graph.spots)} 个节点, {len(data.get('edges', []))} 条边")
    return graph

def get_data_path():
    """获取 campus_map.json 的绝对路径"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 假设数据在 src 的上一级 data 目录中
    return os.path.join(current_dir, '../data/campus_map.json')