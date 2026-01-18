import requests
import random

BASE_URL = "http://127.0.0.1:8000"
# 使用真实账号
USER = "foodie_B"
PASS = "123456"

def main():
    print("🚀 [业务流测试] 模拟完整用户操作...")
    
    # 1. 登录
    print("\nStep 1: 登录...")
    resp = requests.post(f"{BASE_URL}/auth/login", json={"username": USER, "password": PASS})
    if resp.status_code != 200:
        print("❌ 登录失败，请先运行 import_data.py")
        return
    token = resp.json()['access_token']
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ 登录成功")
    
    # 2. 写日记 (针对 '风味餐厅' ID=18)
    print("\nStep 2: 在 '风味餐厅' 发布点评...")
    diary_data = {
        "spot_id": 18,  # ✅ 真实存在的餐厅 ID
        "title": f"风味餐厅实测 {random.randint(1,100)}",
        "content": "这里的饭菜很有特色，值得一来！",
        "score": 4.5
    }
    resp = requests.post(f"{BASE_URL}/diaries/", json=diary_data, headers=headers)
    if resp.status_code == 200:
        new_id = resp.json()['id']
        print(f"✅ 日记发表成功 (ID: {new_id})")
    else:
        print(f"❌ 发表失败: {resp.text}")
        return

    # 3. 自己给自己评论
    print("\nStep 3: 给刚才的日记写评论...")
    comment_data = {
        "diary_id": new_id,
        "content": "补充一下，排队人挺多的。",
        "score": 4.0
    }
    resp = requests.post(f"{BASE_URL}/diaries/comment", json=comment_data, headers=headers)
    if resp.status_code == 200:
        print("✅ 评论成功")
    else:
        print(f"❌ 评论失败: {resp.text}")

    print("\n🎉 流程测试结束！")

if __name__ == "__main__":
    main()