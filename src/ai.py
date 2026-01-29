import json
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from openai import AsyncOpenAI
from sqlmodel import Session, select, or_
import random
import os
from tavily import TavilyClient  # 导入 Tavily 客户端
from datetime import datetime # 导入 datetime 模块

# 导入数据库相关工具
from database import get_session
from models import Diary

# 1. 加载 .env 文件里的变量
load_dotenv()
# 配置 (记得保留你的 Key)在 .env 文件中
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY") # 获取 Tavily 的 Key

# 初始化 OpenAI 客户端
if not DEEPSEEK_API_KEY:
    # 这里我们只是打印警告，没有直接报错退出，防止影响其他功能启动
    # 但如果调用 AI 接口就会报错
    print("⚠️  警告: 未找到 DEEPSEEK_API_KEY 环境变量！AI 功能将无法使用。")
    print("   请在项目根目录创建 .env 文件并填入密钥。")

# 初始化 Tavily 客户端（如果有 Key 的话）
tavily_client = None
if TAVILY_API_KEY:
    tavily_client = TavilyClient(api_key=TAVILY_API_KEY)
else:
    print("⚠️ 警告: 未找到 TAVILY_API_KEY，联网搜索功能将不可用。")

client = AsyncOpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
router = APIRouter(prefix="/ai", tags=["AI Agent"])

class ChatRequest(BaseModel):
    message: str

# ----------------------------------------------------
# 🛠️ 升级版工具函数：支持多关键词“宽容”搜索
# ----------------------------------------------------
def search_database_tool(session: Session, keywords_str: str):
    """
    根据空格分隔的多个关键词去数据库搜索日记
    """
    print(f"🕵️ AI提取的关键词组: {keywords_str}")
    
    keywords = keywords_str.split()
    if not keywords:
        return "没有提取到有效关键词。"

    # 构造查询条件列表：对每个关键词分别在标题和内容上生成匹配条件
    # 说明：
    # - `Diary.title.contains(kw)` 会生成一个 SQL LIKE 条件，用于匹配标题中包含 kw 的记录。
    # - `Diary.content.contains(kw)` 同理，用于匹配内容中包含 kw 的记录。
    # 最终我们会使用 `or_(*conditions)` 将这些条件按“或”组合，
    # 从而得到标题或内容包含任意关键词的日记结果。
    conditions = []
    for kw in keywords:
        # 在标题中查找包含该关键词（等同于 SQL 的 LIKE %kw%）
        conditions.append(Diary.title.contains(kw))
        # 在内容中查找包含该关键词
        conditions.append(Diary.content.contains(kw))
    
    # 1. 先查出所有符合条件的数据 (去掉 limit)
    query = select(Diary).where(or_(*conditions))
    results = session.exec(query).all()
    
    # 2. 如果结果太多，随机抽取 20 条，而不是只取前 5 条
    # 这样能保证 AI 每次可能看到不同的日记，而且涵盖面更广
    if len(results) > 30:
        print(f"   ⚠️ 搜到 {len(results)} 条，随机采样 30 条给 AI...")
        sampled_results = random.sample(results, 30)
    else:
        sampled_results = results
    
    if not sampled_results:
        print("   ❌ 数据库搜索结果: 0 条")
        return "数据库里没有找到相关日记。"
    
    print(f"   ✅ 提供给 AI 的参考日记: {len(sampled_results)} 条")
    
    data_text = ""
    for diary in sampled_results:
        # 我们可以简化一下给 AI 的内容，节省 Token
        data_text += f"- {diary.content} (评分:{diary.score})\n"
    
    return data_text

# 新增：从文本中提取景点的工具
async def extract_spots_from_text(text: str):
    """
    让 AI 从一大段文本中提取出具体的景点名称列表
    """
    system_prompt = """
    你是一个专业的旅游数据分析师。
    请从用户提供的文本中提取出所有的【旅游景点名称】。
    
    要求：
    1. 只输出景点名称，用 JSON 数组格式返回，例如 ["故宫", "天安门", "长城"]
    2. 如果没有发现景点，返回 []
    3. 不要输出任何多余的解释文字，只输出 JSON。
    """
    
    try:
        response = await client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            temperature=0.1
        )
        content = response.choices[0].message.content
        # 清理一下可能的 markdown 标记
        content = content.replace("```json", "").replace("```", "").strip()
        return json.loads(content)
    except Exception as e:
        print(f"❌ AI 提取景点失败: {e}")
        return []

# 定义联网搜索工具函数
def search_internet_tool(query: str):
    """
    使用 Tavily 搜索互联网实时信息
    """
    print(f"🌍 正在联网搜索: {query}")
    
    if not tavily_client:
        return "错误：后端未配置 Tavily API Key，无法联网。"

    try:
        # 调用 Tavily 的搜索接口
        # search_depth="basic" 速度快，"advanced" 搜得深但慢
        response = tavily_client.search(query=query, search_depth="basic", max_results=3)
        
        # Tavily 返回的是一个字典，里面有个 'results' 列表
        results = response.get("results", [])
        
        if not results:
            return "互联网上没有找到相关信息。"
            
        # 把搜到的结果拼成一段文本喂给 AI
        context_text = ""
        for i, result in enumerate(results):
            context_text += f"【来源 {i+1}】{result['content']} (链接: {result['url']})\n"
            
        print(f"   ✅ 联网搜索成功，获取了 {len(results)} 条摘要")
        return context_text

    except Exception as e:
        print(f"   ❌ 搜索出错: {e}")
        return f"搜索过程中发生错误: {str(e)}"
# ----------------------------------------------------
# 🧠 智能 RAG 接口
# ----------------------------------------------------
@router.post("/rag_chat")
async def rag_chat(
    request: ChatRequest, 
    session: Session = Depends(get_session)
):
    user_question = request.message
    
    # [Step 0] 获取当前时间
    # 这一步至关重要！没有它，AI 就不知道"明天"是几号
    current_time = datetime.now().strftime("%Y年%m月%d日 %A")

    # =================================================================
    # [Step 1] 意图识别 (Router) - 大脑核心区
    # =================================================================
    # 我们用 F-String 把时间动态注入到 Prompt 里
    system_prompt_1 = f"""
    ### Role (角色设定)
    你是一个智能意图识别助手。你的唯一任务是分析用户的提问，并决定下一步调用哪个工具。
    不要回答用户的问题，只返回简短的【指令代码】。

    ### Context (当前环境)
    - 当前系统时间：{current_time}
    - 默认地理位置：北京，北京邮电大学(BUPT)
    
    ### Tools (可用工具与触发条件)
    
    1. **本地数据库 (Local DB)**
       - 触发条件：用户询问【校内】相关信息。
       - 覆盖范围：食堂评价、校内景点(如西门、图书馆)、同学的日记、校内生活指南。
       - 返回格式：`DB: <提取2-3个核心关键词>`
    
    2. **互联网搜索 (Internet Search)**
       - 触发条件：用户询问【校外】信息或【实时/时效性】强的信息。
       - 覆盖范围：校外旅游景点(故宫、长城)、实时天气预报、今天的新闻、校外交通路线。
       - 返回格式：`NET: <搜索关键词>`
    
    3. **直接回复 (No Tool)**
       - 触发条件：用户只是打招呼、闲聊、情感交流，或问题不需要任何事实依据。
       - 返回格式：`NONE`

    ### Examples (少样本示例 - 教AI照着学)
    
    User: "学校食堂哪个窗口好吃？"
    Assistant: DB: 食堂 好吃 推荐

    User: "北京明天会下雨吗？"
    Assistant: NET: 北京 明天 天气

    User: "天安门怎么去？"
    Assistant: NET: 北邮 到 天安门 交通路线

    User: "图书馆几点闭馆？"
    Assistant: DB: 图书馆 闭馆时间

    User: "你好呀，你是谁？"
    Assistant: NONE

    ### Constraints (严格约束)
    - 严禁输出任何解释性文字。
    - 严禁把"DB"和"NET"搞混。
    - 如果关键词中有时间词(如"明天")，请保留。
    """
    
    # ... (接下来的代码逻辑) ...
    try:
        # 调用 DeepSeek 进行意图分类
        response1 = await client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt_1},
                {"role": "user", "content": user_question}
            ],
            stream=False # 意图识别不需要流式输出，我们要拿到完整结果再处理
        )
        # 获取 AI 的判断结果 (例如 "NET: 北京 明天 天气")
        intent_result = response1.choices[0].message.content.strip()
        print(f"🤖 [Debug] 意图识别结果: {intent_result}")

        # =================================================================
        # [Step 2] 分支执行 (Switch Case) - 手脚执行区
        # =================================================================
        
        final_context = ""
        source_tag = ""

        # Case A: 查本地库
        if intent_result.startswith("DB:"):
            keywords = intent_result.replace("DB:", "").strip()
            print(f"   🔍 路由至: 本地数据库 (Keywords: {keywords})")
            final_context = search_database_tool(session, keywords)
            source_tag = "本地数据库 (RAG)"
            
        # Case B: 查互联网
        elif intent_result.startswith("NET:"):
            query = intent_result.replace("NET:", "").strip()
            print(f"   🌍 路由至: 互联网搜索 (Query: {query})")
            
            # 【技巧】把当前时间拼接到搜索词里，强制搜索引擎找最新的
            # 比如搜 "明天天气"，变成 "明天天气 (当前: 2026-01-19)"
            # 这样 Tavily 就能搜到正确的预报
            search_query = f"{query} (Current Date: {current_time})"
            final_context = search_internet_tool(search_query)
            source_tag = "互联网搜索 (Tavily)"
            
        # Case C: 闲聊
        else:
            print("   💬 路由至: 纯闲聊模式")
            # 直接回复，不走 RAG 流程，省钱省时间
            final_reply = await client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": user_question}]
            )
            return {"reply": final_reply.choices[0].message.content, "source": "AI闲聊"}

        # =================================================================
        # [Step 3] 最终生成 (Generator) - 整合输出区
        # =================================================================
        
        # 这一步是让 AI 当"编辑"，把搜到的乱七八糟的信息整理成人话
        final_system_prompt = f"""
        【当前时间】：{current_time}
        你是一个贴心的校园导游助手。
        用户问："{user_question}"
        
        我利用工具为你找到了以下参考信息（来源：{source_tag}）：
        =========================================
        {final_context}
        =========================================
        
        请严格基于上述参考信息回答用户的问题。
        - 如果是天气信息，请提醒用户注意保暖或带伞。
        - 如果是食堂评价，可以引用一两条具体的同学评论。
        - 如果参考信息里没有答案，请诚实地说"我没找到相关信息"。
        """
        
        response2 = await client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": final_system_prompt},
                {"role": "user", "content": user_question}
            ]
        )
        return {
            "reply": response2.choices[0].message.content, 
            "source": source_tag
        }

    except Exception as e:
        print(f"❌ 系统错误: {e}")
        # 在生产环境中，这里最好记录详细日志
        raise HTTPException(status_code=500, detail=str(e))
# ==========================================
# ➕ 新增：日记润色接口
# ==========================================
class PolishRequest(BaseModel):
    content: str

@router.post("/polish")
async def polish_diary(request: PolishRequest):
    """
    接收一段文字，让 AI 把它改写得更优美
    """
    user_content = request.content
    system_prompt = "你是一个文学编辑。请润色用户的日记，使其文笔更优美、生动，但不要改变原意。"
    
    try:
        response = await client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ]
        )
        return {"polished": response.choices[0].message.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))