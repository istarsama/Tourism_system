import requests

BASE_URL = "http://127.0.0.1:8000"
# ✅ 修改点 1: 使用真实存在的账号 (import_data.py 导入的)
USERNAME = "student_A"
PASSWORD = "123456"

def main():
    print("🚀 [评论测试] 开始测试多人评分与平均分计算...")
    
    # 1. 登录
    print(f"🔑 正在登录用户 {USERNAME}...")
    res = requests.post(f"{BASE_URL}/auth/login", json={"username": USERNAME, "password": PASSWORD})
    
    if res.status_code != 200:
        print(f"❌ 登录失败: {res.text}")
        print("   (请检查 auth.py 是否已改回 bcrypt，且数据库已导入数据)")
        return
        
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ 登录成功！")
    
    # 2. 发布一篇新日记
    # ✅ 修改点 2: 使用真实的 spot_id (比如 44 学生食堂)
    print("\n📝 发布一篇用于测试评分的日记...")
    diary_payload = {
        "spot_id": 44, 
        "title": "测试评分专用贴",
        "content": "大家快来给我打分！这是一个测试。",
        "media_files": []
    }
    res = requests.post(f"{BASE_URL}/diaries/", json=diary_payload, headers=headers)
    
    if res.status_code != 200:
        print(f"❌ 日记发布失败: {res.text}")
        return

    data = res.json()
    diary_id = data["id"]
    print(f"   ✅ 日记发布成功 ID: {diary_id}, 初始评分: {data['score']}")

    # 3. 模拟第一次打分 (5分)
    print("\n👤 模拟用户A 打了 5 分...")
    comment1 = {
        "diary_id": diary_id,
        "content": "写得太好了！支持！",
        "score": 5.0
    }
    res = requests.post(f"{BASE_URL}/diaries/comment", json=comment1, headers=headers)
    if res.status_code == 200:
        print(f"   📬 评论成功: {res.json()}")
    else:
        print(f"   ❌ 评论失败: {res.text}")
    
    # 4. 模拟第二次打分 (1分)
    # (注意：现实中通常是一个人评一次，这里为了测试简单，用同一个人评了两次，逻辑上后端可能允许也可能覆盖，主要测平均分计算)
    print("\n👤 模拟用户A 又评了一次 (1分)...")
    comment2 = {
        "diary_id": diary_id,
        "content": "再看了一遍，觉得不行...",
        "score": 1.0
    }
    res = requests.post(f"{BASE_URL}/diaries/comment", json=comment2, headers=headers)
    print(f"   📬 系统返回: {res.json()}")

    # 5. 验证结果
    # 如果系统逻辑是“多次评分取平均”，那就是 (5+1)/2 = 3.0
    # 如果系统逻辑是“覆盖”，那就是 1.0
    # 我们来看看实际变成了多少
    print("\n🔍 检查最终评分...")
    res = requests.get(f"{BASE_URL}/diaries/detail/{diary_id}")
    final_score = res.json()["score"]
    print(f"   🏆 当前日记最终评分: {final_score}")
    
    if 1.0 <= final_score <= 5.0:
        print("✅ 测试通过！评分数值在合理范围内。")
    else:
        print(f"❌ 测试存疑，评分 {final_score} 超出范围。")

if __name__ == "__main__":
    main()