import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def run_scenario(name, question, expected_keyword_in_source):
    """
    一个通用的测试函数，用来测不同的场景
    """
    print(f"\n🧪 [测试场景] {name}")
    print(f"   ❓ 提问: {question}")
    
    try:
        # 发送请求
        res = requests.post(f"{BASE_URL}/ai/rag_chat", json={"message": question})
        
        if res.status_code == 200:
            data = res.json()
            reply = data.get('reply', '')
            source = data.get('source', '未知来源')
            
            # 打印结果
            print(f"   🤖 AI 回复: {reply[:60]}...") # 只打印前60个字避免刷屏
            print(f"   📜 实际来源: {source}")
            
            # 验证来源是否符合预期
            if expected_keyword_in_source in source:
                print(f"   ✅ 测试通过！成功识别意图。")
            else:
                print(f"   ⚠️ 警告: 来源不符 (预期包含 '{expected_keyword_in_source}')")
        else:
            print(f"   ❌ 请求失败: {res.text}")
            
    except Exception as e:
        print(f"   ❌ 连接错误: {e}")

def main():
    print("🤖 开始全能 AI 导游测试 (数据库 + 联网 + 闲聊)...")
    print("(请确保后端已重启，且 .env 里配置了 DEEPSEEK_API_KEY 和 TAVILY_API_KEY)")

    # ---------------------------------------------------------
    # 场景 1: 纯闲聊 (应该直接回答，不查任何东西)
    # ---------------------------------------------------------
    run_scenario(
        name="纯闲聊模式",
        question="你好呀，给我讲个冷笑话",
        expected_keyword_in_source="AI闲聊"
    )

    # ---------------------------------------------------------
    # 场景 2: 查本地数据库 (应该查 MySQL 日记)
    # ---------------------------------------------------------
    # 只要你运行过 import_data.py，库里就有关于"食堂"的数据
    run_scenario(
        name="RAG 查库模式",
        question="根据同学们的反馈，学生食堂的饭怎么样？",
        expected_keyword_in_source="本地数据库"
    )

    # ---------------------------------------------------------
    # 场景 3: 查互联网 (应该调用 Tavily)
    # ---------------------------------------------------------
    # 问一个库里绝对没有、且具有时效性的问题
    run_scenario(
        name="联网搜索模式",
        question="北京明天天气怎么样？适合穿什么衣服？",
        expected_keyword_in_source="互联网搜索"
    )

if __name__ == "__main__":
    main()
