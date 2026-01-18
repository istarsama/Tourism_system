import requests

BASE_URL = "http://127.0.0.1:8000"

def main():
    print("🧠 开始测试 RAG (AI + 私有数据库)...")
    
    # 场景 1：普通聊天
    print("\n💬 测试 1: 打招呼 (不应该查库)")
    res = requests.post(f"{BASE_URL}/ai/rag_chat", json={"message": "你好呀，你是谁？"})
    print(f"🤖 AI: {res.json().get('reply')}")

    # 场景 2：查库
    # 假设你之前发布过关于“食堂”或“烤鸭”的日记
    print("\n🕵️ 测试 2: 询问数据库里的知识")
    question = "根据大家的日记，学校食堂的饭好吃吗？"
    print(f"❓ 问: {question}")
    
    res = requests.post(f"{BASE_URL}/ai/rag_chat", json={"message": question})
    data = res.json()
    print(f"📜 来源: {data.get('source', '纯闲聊')}")
    print(f"🤖 AI: {data.get('reply')}")

if __name__ == "__main__":
    main()