import requests

BASE_URL = "http://127.0.0.1:8000"

def main():
    print("🤖 [AI 测试] 开始测试智能 RAG 功能...")
    print("(⚠️ 请确保 .env 里填了 Key，且后端已重启)")

    # 场景 1：普通闲聊 (测试 AI 是否活着)
    print("\n💬 测试 1: 普通闲聊 (不应该查库)")
    msg1 = "你好呀，给我讲个冷笑话"
    try:
        res = requests.post(f"{BASE_URL}/ai/rag_chat", json={"message": msg1})
        if res.status_code == 200:
            data = res.json()
            print(f"   🤖 AI: {data['reply'][:50]}...") # 只打印前50个字
            # 如果 source 不在返回里，说明是直接回答的，没查库
            print(f"   📜 来源: {data.get('source', '纯闲聊')}")
        else:
            print(f"   ❌ 失败: {res.text}")
    except Exception as e:
        print(f"   ❌ 连接错误: {e}")

    # 场景 2：知识库问答 (测试是否能在数据库里搜到东西)
    # 只要你运行过 import_data.py，库里就有关于"食堂"的日记
    print("\n🕵️ 测试 2: 知识库问答 (应该查库)")
    msg2 = "根据同学们的反馈，学生食堂的饭怎么样？"
    try:
        res = requests.post(f"{BASE_URL}/ai/rag_chat", json={"message": msg2})
        if res.status_code == 200:
            data = res.json()
            print(f"   🤖 AI: {data['reply'][:50]}...")
            print(f"   📜 来源: {data.get('source', '未命中')}")
            
            if "已检索" in data.get('source', ''):
                print("   ✅ RAG 成功！AI 读取了你的数据库！")
            else:
                print("   ⚠️ RAG 未触发，可能是关键词提取失败或库里没数据。")
        else:
            print(f"   ❌ 失败: {res.text}")
    except Exception as e:
        print(f"   ❌ 连接错误: {e}")

if __name__ == "__main__":
    main()