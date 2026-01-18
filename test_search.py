import requests
import sys

# 1. 放在最前面，确保脚本只要运行就会说话
print("👋 脚本开始运行了！")

# 配置
BASE_URL = "http://127.0.0.1:8000"
USERNAME = "xiaoming"  
PASSWORD = "my_secret_password_123" 

def main():
    print("🚀 进入 main 函数，开始测试...")
    
    # --- 1. 登录 ---
    print(f"🔑 正在尝试登录用户: {USERNAME} ...")
    try:
        # 注意：这里用的是 json=... 而不是 data=...
        login_res = requests.post(f"{BASE_URL}/auth/login", json={
            "username": USERNAME, "password": PASSWORD
        })
    except requests.exceptions.ConnectionError:
        print("❌ 连接服务器失败！请确认后端(main.py)是否正在运行？")
        return

    if login_res.status_code != 200:
        print(f"❌ 登录失败! 状态码: {login_res.status_code}")
        print(f"   错误信息: {login_res.text}")
        return
        
    token_data = login_res.json()
    token = token_data.get("access_token")
    if not token:
        print(f"❌ 获取Token失败，响应内容: {token_data}")
        return

    headers = {"Authorization": f"Bearer {token}"}
    print("✅ 登录成功！")
    
    # --- 2. 发布日记 ---
    print("\n📝 正在发布测试日记...")
    diaries_data = [
        {"title": "北邮的秋天", "content": "银杏大道的叶子黄了，非常美！", "score": 5.0},
        {"title": "食堂测评", "content": "新食堂的烤鸭饭真的很好吃。", "score": 4.5},
        {"title": "找不到教室", "content": "教三楼真的太像迷宫了...", "score": 3.0}
    ]
    
    ids = []
    for data in diaries_data:
        payload = {
            "spot_id": 1, 
            "title": data["title"],
            "content": data["content"],
            "score": data["score"],
            "media_files": []
        }
        res = requests.post(f"{BASE_URL}/diaries/", json=payload, headers=headers)
        if res.status_code == 200:
            ids.append(res.json()["id"])
            print(f"   ✅ 发布成功: 《{data['title']}》")
        else:
            print(f"   ❌ 发布失败: {res.text}")
            
    if len(ids) < 2:
        print("⚠️ 数据不足，停止测试")
        return

    # --- 3. 刷热度 ---
    target_id = ids[1] 
    print(f"\n🔥 正在围观《食堂测评》 (ID: {target_id})...")
    for _ in range(5):
        requests.get(f"{BASE_URL}/diaries/detail/{target_id}")
    print("   (热度已增加)")

    # --- 4. 推荐测试 ---
    print("\n🔍 测试 1: 热门推荐")
    res = requests.get(f"{BASE_URL}/diaries/search?sort_by=heat")
    diaries = res.json()
    
    if diaries:
        top_one = diaries[0]
        print(f"   🏆 第一名: 《{top_one['title']}》 (热度: {top_one['view_count']})")
        if "食堂" in top_one['title']:
            print("   ✅ 推荐功能正常！")
        else:
            print("   ❌ 推荐功能异常。")
    else:
        print("   ❌ 未查到数据")

    # --- 5. 搜索测试 ---
    keyword = "银杏"
    print(f"\n🔍 测试 2: 搜索 '{keyword}'")
    res = requests.get(f"{BASE_URL}/diaries/search?keyword={keyword}")
    results = res.json()
    
    if len(results) > 0 and keyword in results[0]['content']:
        print(f"   ✅ 找到: 《{results[0]['title']}》")
        print("   ✅ 搜索功能正常！")
    else:
        print("   ❌ 搜索失败")

# ==========================================
# 👇 最关键就是这两行！千万不要漏掉！
# ==========================================
if __name__ == "__main__":
    main()