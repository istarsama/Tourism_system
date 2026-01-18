import requests

# ✅ 使用 mock_data.json 里导入的真实账号
# 这样你不需要手动注册就能测登录
USERNAME = "student_A" 
PASSWORD = "123456"    # import_data.py 里硬编码的默认密码

def main():
    print(f"🕵️ [登录测试] 尝试登录: {USERNAME} ...")
    
    try:
        resp = requests.post("http://127.0.0.1:8000/auth/login", json={
            "username": USERNAME, 
            "password": PASSWORD
        })
        
        if resp.status_code == 200:
            data = resp.json()
            print("\n✅ 登录成功！")
            print(f"🎫 Access Token: {data['access_token'][:20]}...") 
            print("   (Token 有效，可以用于后续测试)")
        else:
            print(f"\n❌ 登录失败: {resp.text}")

    except Exception as e:
        print(f"❌ 服务未启动或连接错误: {e}")

if __name__ == "__main__":
    main()