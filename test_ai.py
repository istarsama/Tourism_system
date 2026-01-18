import requests

BASE_URL = "http://127.0.0.1:8000"

def main():
    print("🤖 开始测试 DeepSeek AI 功能...")
    print("(⚠️ 注意：如果你没有填写真实的 API Key，这一步会报错)")

    # 1. 测试聊天
    print("\n💬 测试 1: 问 AI 一个问题...")
    question = "北邮哪个食堂的饭最好吃？"
    try:
        res = requests.post(f"{BASE_URL}/ai/chat", json={"message": question})
        if res.status_code == 200:
            print(f"   🤖 AI 回复: {res.json()['reply']}")
        else:
            print(f"   ❌ 请求失败: {res.text}")
    except Exception as e:
        print(f"   ❌ 连不上服务器: {e}")

    # 2. 测试日记润色
    print("\n✨ 测试 2: 让 AI 帮我写日记...")
    raw_content = "今天天气不错，我和室友去看了银杏，黄色的叶子很好看，人很多。"
    try:
        res = requests.post(f"{BASE_URL}/ai/polish", json={"content": raw_content})
        if res.status_code == 200:
            print(f"   📝 原文: {raw_content}")
            print(f"   ✨ 润色后: {res.json()['polished']}")
        else:
            print(f"   ❌ 请求失败: {res.text}")
    except Exception as e:
        print(f"   ❌ 连不上服务器: {e}")

if __name__ == "__main__":
    main()