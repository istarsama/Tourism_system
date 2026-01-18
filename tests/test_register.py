import requests # 如果报错没这个库，先运行 uv add requests

# 1. 定义要注册的用户信息
data = {
    "username": "xiaoming",  # 你可以随便改名字
    "password": "my_secret_password_123"
}

# 2. 发送请求给后端
print(f"正在尝试注册用户: {data['username']} ...")
try:
    # 注意：如果你是在本地跑，地址是 127.0.0.1:8000
    response = requests.post("http://127.0.0.1:8000/auth/register", json=data)
    
    # 3. 打印结果
    if response.status_code == 200:
        print("✅ 注册成功！")
        print("后端返回:", response.json())
    else:
        print("❌ 注册失败")
        print("错误信息:", response.text)

except Exception as e:
    print(f"❌ 请求发送失败: {e}")