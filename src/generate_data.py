import json
import random
import math
import os

# 配置参数
OUTPUT_DIR = "data"
OUTPUT_FILE = "campus_map.json"
MAP_SIZE = 1000
MIN_NODES = 200
EXTRA_EDGES = 100  # 在生成树基础上增加的随机边数量

# 名字生成的配置
NAME_CONFIG = {
    "gate": ["东门", "西门", "南门", "北门", "东南门"],
    "canteen": ["学一食堂", "学二食堂", "清真食堂", "教工食堂", "风味餐厅", "美食广场", "西区食堂", "东区食堂", "夜宵档", "咖啡厅"],
    "sight": ["图书馆", "校史馆", "荷花池", "名人雕像", "中心花园", "喷泉广场", "大礼堂", "体育馆", "游泳馆", "天文台", "静心湖", "钟楼", "银杏大道", "情人坡", "老校门"],
    # 剩下的通过循环生成
    "building_prefix": ["教", "实验楼", "行政楼", "科研楼", "综合楼"],
    "dorm_prefix": ["南区宿舍", "北区宿舍", "研究生公寓", "留学生楼"]
}

DESCRIPTIONS = [
    "这里环境优美，适合拍照。", "平常这里人比较多。", "是学校的标志性建筑。", 
    "很多同学喜欢在这里晨读。", "刚刚翻新过，设施很新。", "这也是很多猫咪聚集的地方。",
    "历史悠久的建筑。", "你需要刷卡才能进入。", "这里Wi-Fi信号很好。", "比较偏僻，注意安全。"
]

def calculate_dist(n1, n2):
    """计算两个节点间的欧几里得距离"""
    return math.sqrt((n1['x'] - n2['x'])**2 + (n1['y'] - n2['y'])**2)

def generate_nodes():
    nodes = []
    node_id = 0

    # 1. 生成固定名字的节点 (Gate, Canteen, Sight)
    for cat in ["gate", "canteen", "sight"]:
        for name in NAME_CONFIG[cat]:
            nodes.append({
                "id": node_id,
                "name": name,
                "category": cat,
                "x": random.randint(50, MAP_SIZE - 50),
                "y": random.randint(50, MAP_SIZE - 50),
                "desc": random.choice(DESCRIPTIONS)
            })
            node_id += 1

    # 2. 循环生成教学楼 (Building) - 约 50 个
    for i in range(1, 51):
        # 随机分配前缀，例如 "教1楼", "实验楼3号"
        prefix = random.choice(NAME_CONFIG["building_prefix"])
        suffix = f"{i}号楼" if "楼" not in prefix else f"{i}"
        if prefix == "教": suffix = f"{i}楼"
        
        nodes.append({
            "id": node_id,
            "name": f"{prefix}{suffix}",
            "category": "building",
            "x": random.randint(100, MAP_SIZE - 100),
            "y": random.randint(100, MAP_SIZE - 100),
            "desc": f"这是{prefix}{suffix}，主要用于日常教学和办公。"
        })
        node_id += 1

    # 3. 循环生成宿舍 (Dorm) - 补足到至少 200 个以上
    dorm_count = 1
    while len(nodes) < 220: # 生成到 220 个节点
        prefix = random.choice(NAME_CONFIG["dorm_prefix"])
        nodes.append({
            "id": node_id,
            "name": f"{prefix}{dorm_count}号楼",
            "category": "dorm",
            "x": random.randint(50, MAP_SIZE - 50),
            "y": random.randint(50, MAP_SIZE - 50),
            "desc": "学生休息区域，保持安静。"
        })
        node_id += 1
        dorm_count += 1

    print(f"✅ 生成节点总数: {len(nodes)}")
    return nodes

def generate_edges(nodes):
    edges = []
    connected_ids = {nodes[0]['id']} # 已连接到主图的节点ID集合
    remaining_ids = [n['id'] for n in nodes[1:]] # 尚未连接的节点ID列表

    # --- 第一阶段：构建骨架 (保证连通性) ---
    # 逻辑：每次从“未连接集合”中取出一个节点，连接到“已连接集合”中距离它最近的那个点。
    # 这类似 Prim 算法的思想，生成的图路网比较自然，不会出现超长连线。
    
    
    while remaining_ids:
        # 随机取一个未连接的点（为了打乱顺序，避免线性偏向）
        current_id = remaining_ids.pop(random.randint(0, len(remaining_ids) - 1))
        current_node = next(n for n in nodes if n['id'] == current_id)

        # 在已连接的节点中寻找距离最近的点
        nearest_id = -1
        min_dist = float('inf')

        for cid in connected_ids:
            target_node = next(n for n in nodes if n['id'] == cid)
            d = calculate_dist(current_node, target_node)
            if d < min_dist:
                min_dist = d
                nearest_id = cid
        
        # 添加这条骨干边
        edges.append({
            "u": current_id,
            "v": nearest_id,
            "dist": round(min_dist, 2),
            "type": "walk", # 骨干路默认为步行
            "crowding": round(random.uniform(0.5, 1.5), 2)
        })
        connected_ids.add(current_id)

    print(f"✅ 骨架构建完成，当前边数: {len(edges)}")

    # --- 第二阶段：添加随机边 (增加复杂度) ---
    # 随机连接两个点，模拟捷径或骑行道
    added_count = 0
    while added_count < EXTRA_EDGES:
        u = random.choice(nodes)
        v = random.choice(nodes)

        # 避免自环
        if u['id'] == v['id']:
            continue
        
        # 避免重复边 (检查是否已经存在 u-v 或 v-u)
        exists = False
        for e in edges:
            if (e['u'] == u['id'] and e['v'] == v['id']) or \
               (e['u'] == v['id'] and e['v'] == u['id']):
                exists = True
                break
        
        if not exists:
            dist = calculate_dist(u, v)
            # 只有距离不太远的点才连接，避免横跨整个地图的奇怪路线
            if dist < 300: 
                edges.append({
                    "u": u['id'],
                    "v": v['id'],
                    "dist": round(dist, 2),
                    "type": random.choice(["walk", "bike"]),
                    "crowding": round(random.uniform(0.5, 2.0), 2)
                })
                added_count += 1

    print(f"✅ 随机边添加完成，总边数: {len(edges)}")
    return edges

def main():
    # 1. 确保目录存在
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"📂 创建目录: {OUTPUT_DIR}")

    # 2. 生成数据
    nodes = generate_nodes()
    edges = generate_edges(nodes)

    data = {
        "nodes": nodes,
        "edges": edges
    }

    # 3. 写入文件
    filepath = os.path.join(OUTPUT_DIR, OUTPUT_FILE)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    
    print(f"🎉 数据生成成功！已保存至: {filepath}")
    print(f"   - 节点数: {len(nodes)}")
    print(f"   - 边数: {len(edges)}")

if __name__ == "__main__":
    main()