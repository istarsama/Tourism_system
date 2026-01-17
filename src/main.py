# src/main.py
import json
import os
from models import CampusGraph, Spot

def load_graph_from_json(filepath):
    """读取JSON文件并构建图"""
    graph = CampusGraph()
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    # 1. 加载节点
    for node in data['nodes']:
        spot = Spot(node['id'], node['name'], node['category'], 
                    node['x'], node['y'], node['desc'])
        graph.add_spot(spot)
        
    # 2. 加载边
    for edge in data['edges']:
        graph.add_edge(edge['u'], edge['v'], edge['dist'], 
                       edge['type'], edge['crowding'])
                       
    return graph

if __name__ == "__main__":
    # 定位数据文件路径
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 修改点：直接拼接文件名，因为 test.json 就在 src 文件夹里（和代码同级）
    data_path = os.path.join(current_dir, 'test.json') 
    # 构图
    my_campus = load_graph_from_json(data_path)
    
    print("✅ 地图加载成功！")
    print(f"当前包含景点数量: {len(my_campus.spots)}")
    print(f"节点1（{my_campus.get_spot_name(1)}）连接了:")
    for road in my_campus.adj[1]:
        neighbor_name = my_campus.get_spot_name(road.v)
        print(f"  -> 去往 {neighbor_name}, 距离: {road.distance}m, 拥挤度: {road.crowding}")