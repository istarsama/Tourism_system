import os
import json
from models import CampusGraph, Spot, Road

# 引入刚才写的算法
from algorithms import dijkstra_search

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
        # 注意：这里读取JSON里的各个字段
        graph.add_edge(edge['u'], edge['v'], edge['dist'], 
                       edge['type'], edge['crowding'])
                       
    return graph

if __name__ == "__main__":
    # 1. 定位数据文件路径 (兼容性写法)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 注意：这里文件名必须和你 data 文件夹里的实际文件名一致
    # 如果你没改名，依然用 test.json；如果改成了 campus_map.json 请同步修改这里
    data_path = os.path.join(current_dir, '../data/campus_map.json') 
    
    # 2. 构建图
    if not os.path.exists(data_path):
        print(f"❌ 错误：找不到数据文件 {data_path}")
    else:
        my_campus = load_graph_from_json(data_path)
        print("✅ 地图加载成功！\n")

        # --- 测试导航功能 ---
        start_node = 1  # 北邮西门
        end_node = 3    # 主楼 (根据之前的数据，1->2->3 是通的)

        print(f"🚗 导航请求: 从 [{my_campus.get_spot_name(start_node)}] 到 [{my_campus.get_spot_name(end_node)}]")
        
        # 调用 Dijkstra
        path_ids, cost = dijkstra_search(my_campus, start_node, end_node, criterion='dist')
        
        if not path_ids:
            print("❌ 无法到达目的地")
        else:
            # 将 ID 列表转换为名称列表，方便阅读
            path_names = [my_campus.get_spot_name(pid) for pid in path_ids]
            print(f"🎉 规划成功 (总距离 {cost}m):")
            print(" -> ".join(path_names))