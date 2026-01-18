import json
import requests

# 配置
BASE_URL = "http://127.0.0.1:8000"
USERNAME = "xiaoming"       # 确保这个用户存在
PASSWORD = "my_secret_password_123"

def import_mock_data():
    # 1. 先登录拿到 Token
    print(f"🔑 正在登录用户 {USERNAME}...")
    login_res = requests.post(f"{BASE_URL}/auth/login", json={
        "username": USERNAME, "password": PASSWORD
    })
    
    if login_res.status_code != 200:
        print("❌ 登录失败，请检查账号密码或后端是否启动")
        return
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. 读取 JSON 文件
    try:
        with open("mock_data.json", "r", encoding="utf-8") as f:
            data_list = json.load(f)
    except FileNotFoundError:
        print("❌ 没找到 mock_data.json，请先让 AI 生成数据并保存！")
        return

    # 3. 循环发送请求
    print(f"🚀 开始导入 {len(data_list)} 条数据...")
    success_count = 0
    for item in data_list:
        try:
            res = requests.post(f"{BASE_URL}/diaries/", json=item, headers=headers)
            if res.status_code == 200:
                print(f"   ✅ 导入成功: {item['title']}")
                success_count += 1
            else:
                print(f"   ❌ 导入失败: {res.text}")
        except Exception as e:
            print(f"   ⚠️ 请求出错: {e}")

    print(f"\n🎉 导入完成！成功: {success_count}/{len(data_list)}")

if __name__ == "__main__":
    import_mock_data()