import requests

BASE_URL = "http://127.0.0.1:8000"

def main():
    print("🔍 [搜索测试] 开始测试搜索功能...")

    # 1. 搜日记
    keyword = "食堂"  # mock_data 里肯定有关于食堂的日记
    print(f"\n📋 测试 1: 搜索日记关键词 '{keyword}'")
    
    try:
        res = requests.get(f"{BASE_URL}/diaries/search?keyword={keyword}")
        results = res.json()
        
        if len(results) > 0:
            print(f"   ✅ 找到 {len(results)} 篇日记")
            print(f"   Example: 《{results[0]['title']}》")
        else:
            print("   ⚠️ 未找到数据，请确认 import_data.py 是否运行")
            
    except Exception as e:
        print(f"❌ 错误: {e}")

    # 2. 搜地点 (模糊搜索)
    spot_name = "学一"
    print(f"\n📍 测试 2: 搜索地点 '{spot_name}'")
    res = requests.get(f"{BASE_URL}/spots/search?query={spot_name}")
    data = res.json()
    
    if data:
        print(f"   ✅ 找到地点: {data[0]['name']} (ID: {data[0]['id']})")
    else:
        print("   ❌ 未找到地点")

if __name__ == "__main__":
    main()