import requests

BASE_URL = "http://127.0.0.1:8000"

def main():
    print("🚀 开始全流程测试...\n")
    
    # 1. 登录 (获取 Token)
    print("Step 1: 登录...")
    login_data = {"username": "xiaoming", "password": "my_secret_password_123"}
    resp = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    
    if resp.status_code != 200:
        print("❌ 登录失败，请检查账号密码")
        return
        
    token = resp.json()['access_token']
    print(f"✅ 拿到 Token: {token[:10]}...")
    
    # 2. 写日记 (带上 Token!)
    print("\nStep 2: 在 '学一食堂' (假设ID是1) 写日记...")
    
    diary_data = {
        "spot_id": 1,
        "title": "太好吃了",
        "content": "今天的麻辣香锅绝了，推荐大家来吃！",
        "score": 4.8
    }
    
    # 🔑 关键：把 Token 放在 Header 里
    headers = {"Authorization": f"Bearer {token}"}
    
    resp = requests.post(f"{BASE_URL}/diaries/", json=diary_data, headers=headers)
    
    if resp.status_code == 200:
        print("✅ 日记发表成功！后端返回:", resp.json())
    else:
        print("❌ 发表失败:", resp.text)
        
    # 3. 查看日记 (不需要 Token)
    print("\nStep 3: 刷新 '学一食堂' 的评论区...")
    resp = requests.get(f"{BASE_URL}/diaries/1")
    print("✅ 当前评论列表:", resp.json())

if __name__ == "__main__":
    main()