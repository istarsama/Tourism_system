import requests

BASE_URL = "http://127.0.0.1:8000"

def main():
    print("🗺️  [导航测试] 开始测试路径规划...")

    # ==========================================
    # 场景 1: 长距离导航 (西门 -> 学生食堂)
    # ==========================================
    print("\n🏃 [测试 1] 西门(1) -> 学生食堂(44)")
    payload = {
        "start_id": 1, 
        "end_id": 44,  # ✅ 这是一个真实存在的点
        "strategy": "dist",
        "transport": "walk"
    }
    
    try:
        res = requests.post(f"{BASE_URL}/navigate", json=payload)
        if res.status_code == 200:
            data = res.json()
            print(f"   ✅ 规划成功!")
            print(f"   📍 路径: {data['path_names']}")
            print(f"   📏 距离: {data['total_cost']} {data['cost_unit']}")
        else:
            print(f"   ❌ 失败: {res.text}")

        # ==========================================
        # 场景 2: 多点规划 (西门 -> 经由图书馆 -> 南门)
        # ==========================================
        print("\n🔗 [测试 2] 多点规划: 西门(1) -> 途经图书馆(57) -> 南门(7)")
        payload_multi = {
            "start_id": 1,
            "end_id": 7,      # 南门
            "via_ids": [57],  # ✅ 图书馆 (ID 57 肯定存在)
            "strategy": "dist",
            "transport": "bike"
        }
        res = requests.post(f"{BASE_URL}/navigate", json=payload_multi)
        
        if res.status_code == 200:
            data = res.json()
            print(f"   ✅ 多点规划成功!")
            print(f"   🗺️ 路线: {data['path_names']}")
        else:
            print(f"   ❌ 失败: {res.text}")

    except Exception as e:
        print(f"❌ 连接失败: {e}")

if __name__ == "__main__":
    main()