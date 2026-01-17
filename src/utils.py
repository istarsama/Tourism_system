import json
import os
from models import CampusGraph, Spot

def load_graph_from_json(filepath):
    """读取JSON文件并构建图的通用函数"""
    graph = CampusGraph()
    
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"数据文件不存在: {filepath}")

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    for node in data['nodes']:
        # 兼容一下有时候 json 里可能没有 desc 字段的情况
        desc = node.get('desc', "")
        spot = Spot(node['id'], node['name'], node['category'], 
                    node['x'], node['y'], desc)
        graph.add_spot(spot)
        
    for edge in data['edges']:
        graph.add_edge(edge['u'], edge['v'], edge['dist'], 
                       edge['type'], edge['crowding'])
                       
    return graph

def get_data_path():
    """获取 campus_map.json 的绝对路径"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 假设数据在 src 的上一级 data 目录中
    return os.path.join(current_dir, '../data/campus_map.json')