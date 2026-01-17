import requests

# 1. 准备登录信息
# 注意：这里必须用你刚才 'test_register.py' 里注册成功的那个账号密码
login_data = {
    "username": "xiaoming", 
    "password": "my_secret_password_123"
}

print(f"🕵️ 正在尝试登录用户: {login_data['username']} ...")

try:
    # 2. 发送登录请求 (POST /auth/login)
    # 这一步后端会读取 .env 里的密钥，加密生成 Token
    resp = requests.post("http://127.0.0.1:8000/auth/login", json=login_data)
    
    # 3. 检查结果
    if resp.status_code == 200:
        result = resp.json()
        print("\n✅ 登录成功！系统工作正常！")
        print("-" * 30)
        print("🎫 你的 Access Token (通行证):")
        print(result['access_token']) # 打印出那串很长的乱码
        print("-" * 30)
        print("💡 下一步：我们要把这个 Token 复制下来，用来发日记。")
    else:
        print("\n❌ 登录失败")
        print(f"状态码: {resp.status_code}")
        print("错误信息:", resp.json())

except Exception as e:
    print(f"❌ 请求发送失败: {e}")
    print("请检查：后端服务(窗口A)是不是还在运行？")