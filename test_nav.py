import requests
import json
import time

# 配置
BASE_URL = "http://127.0.0.1:8000"

def main():
    print("🗺️  开始测试高级路径规划算法...")
    print("------------------------------------------------------")
    
    # ==========================================
    # 测试场景 1: 基础导航 (步行 + 最短距离)
    # ==========================================
    print("\n🏃 [测试 1] 单点导航: 步行 (Walk) + 最短距离 (Dist)")
    payload_1 = {
        "start_id": 1, 
        "end_id": 10,   # 假设去 ID=10 的景点
        "strategy": "dist",
        "transport": "walk"
    }
    try:
        res = requests.post(f"{BASE_URL}/navigate", json=payload_1)
        if res.status_code == 200:
            data = res.json()
            print(f"   ✅ 规划成功!")
            print(f"   📍 路径: {data['path_names']}")
            print(f"   📏 开销: {data['total_cost']} {data['cost_unit']}")
            cost_walk = data['total_cost']
        else:
            print(f"   ❌ 失败: {res.text}")
            return
    except Exception as e:
        print(f"   ❌ 连接失败，请检查后端是否启动: {e}")
        return

    # ==========================================
    # 测试场景 2: 对比测试 (自行车 + 最短时间)
    # 验证 PPT 考点: "不同交通工具可以选择...时间最短"
    # ==========================================
    print("\n🚴 [测试 2] 单点导航: 自行车 (Bike) + 最短时间 (Time)")
    payload_2 = {
        "start_id": 1, 
        "end_id": 10, 
        "strategy": "time",     # 策略变了
        "transport": "bike"     # 交通工具变了
    }
    res = requests.post(f"{BASE_URL}/navigate", json=payload_2)
    if res.status_code == 200:
        data = res.json()
        print(f"   ✅ 规划成功!")
        print(f"   📍 路径: {data['path_names']}")
        print(f"   ⏱️ 开销: {data['total_cost']} {data['cost_unit']}")
        
        # 简单的验证逻辑
        if data['cost_unit'] == "秒":
            print("   ✨ 验证通过: 单位已自动切换为'秒'")
        else:
            print("   ⚠️ 警告: 单位未切换")
    else:
        print(f"   ❌ 失败: {res.text}")

    # ==========================================
    # 测试场景 3: 多点规划 (TSP 近似)
    # 验证 PPT 考点: "参观多个景点...最优旅游线路"
    # ==========================================
    print("\n🔗 [测试 3] 多点连线规划: 1 -> [3, 5, 8]")
    payload_multi = {
        "start_id": 1,
        "via_ids": [3, 5, 8], # 中间想去这三个地方，顺序由算法决定
        "strategy": "dist",
        "transport": "walk"
    }
    res = requests.post(f"{BASE_URL}/navigate", json=payload_multi)
    if res.status_code == 200:
        data = res.json()
        print(f"   ✅ 多点规划成功!")
        print(f"   🗺️ 推荐游览顺序: {data['path_names']}")
        print(f"   👣 总路程: {data['total_cost']} 米")
        
        # 验证是否经过了所有点
        if len(data['path_ids']) >= 4:
            print("   ✨ 验证通过: 路径覆盖了多个节点")
    else:
        print(f"   ❌ 失败: {res.text}")
        print("   (如果提示 ID 不存在，可能是地图数据太少，请尝试改小 ID)")

if __name__ == "__main__":
    main()