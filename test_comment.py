import requests

BASE_URL = "http://127.0.0.1:8000"
USERNAME = "xiaoming"
PASSWORD = "my_secret_password_123"

def main():
    print("🚀 开始测试：多人评分与平均分计算...")
    
    # 1. 登录
    print(f"🔑 登录用户 {USERNAME}...")
    res = requests.post(f"{BASE_URL}/auth/login", json={"username": USERNAME, "password": PASSWORD})
    if res.status_code != 200:
        print("❌ 登录失败")
        return
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. 发布一篇新日记 (注意：现在发布时没有 score 参数了)
    print("\n📝 发布一篇待评分的日记...")
    diary_payload = {
        "spot_id": 1,
        "title": "测试评分功能的日记",
        "content": "大家快来给我打分！",
        "media_files": []
    }
    res = requests.post(f"{BASE_URL}/diaries/", json=diary_payload, headers=headers)
    diary_id = res.json()["id"]
    print(f"   ✅ 日记发布成功 ID: {diary_id}, 初始评分: {res.json()['score']}")

    # 3. 模拟第一次打分 (5分)
    print("\n👤 用户A 觉得很赞，打了 5 分...")
    comment1 = {
        "diary_id": diary_id,
        "content": "写得太好了！",
        "score": 5.0
    }
    res = requests.post(f"{BASE_URL}/diaries/comment", json=comment1, headers=headers)
    print(f"   📬 系统返回: {res.json()}")
    
    # 4. 模拟第二次打分 (1分)
    print("\n👤 用户B 觉得很烂，打了 1 分...")
    comment2 = {
        "diary_id": diary_id,
        "content": "完全看不懂...",
        "score": 1.0
    }
    res = requests.post(f"{BASE_URL}/diaries/comment", json=comment2, headers=headers)
    print(f"   📬 系统返回: {res.json()}")

    # 5. 验证结果 (5分 + 1分) / 2 = 3.0分
    print("\n🔍 检查最终评分 (预期应该是 3.0)...")
    res = requests.get(f"{BASE_URL}/diaries/detail/{diary_id}")
    final_score = res.json()["score"]
    print(f"   🏆 当前日记评分: {final_score}")
    
    if final_score == 3.0:
        print("✅ 测试通过！评分逻辑完美！")
    else:
        print(f"❌ 测试失败，预期 3.0，实际 {final_score}")

if __name__ == "__main__":
    main()