import os
import json

def check_all_spots():
    print("\n--- 正在从 campus_map.json 读取所有景点 ID ---")
    try:
        # 获取 JSON 文件路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(current_dir, 'data', 'campus_map.json')
        
        if not os.path.exists(json_path):
            print(f"❌ 找不到文件: {json_path}")
            return
        
        # 读取 JSON 文件
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        spots = data.get('spots', [])
        
        if not spots:
            print("❌ 地图数据里没有景点，请检查 campus_map.json")
            return
        
        # 只显示 type="spot" 的景点，过滤掉 type="road" 的路点
        spot_list = [s for s in spots if s.get('type') == 'spot']
        
        if not spot_list:
            print("❌ 没有找到景点（只有路点）")
            return
        
        # 打印表格表头
        print(f"\n{'ID':<6} | {'景点名称':<20} | {'坐标(x,y)'}")
        print("-" * 50)
        
        for spot in spot_list:
            spot_id = spot.get('id', '?')
            name = spot.get('name', '未知')
            x = spot.get('x', 0)
            y = spot.get('y', 0)
            print(f"{spot_id:<6} | {name:<20} | ({x}, {y})")
        
        print(f"\n✅ 共找到 {len(spot_list)} 个景点")
        
    except Exception as e:
        print(f"❌ 读取文件失败: {e}")

if __name__ == "__main__":
    check_all_spots()