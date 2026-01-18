import json
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from openai import AsyncOpenAI
from sqlmodel import Session, select, or_
import random
import os

# 导入数据库相关工具
from database import get_session
from models import Diary

# 1. 加载 .env 文件里的变量
load_dotenv()
# 配置 (记得保留你的 Key)
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"

if not DEEPSEEK_API_KEY:
    # 这里我们只是打印警告，没有直接报错退出，防止影响其他功能启动
    # 但如果调用 AI 接口就会报错
    print("⚠️  警告: 未找到 DEEPSEEK_API_KEY 环境变量！AI 功能将无法使用。")
    print("   请在项目根目录创建 .env 文件并填入密钥。")

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

    conditions = []
    for kw in keywords:
        conditions.append(Diary.title.contains(kw))
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

# ----------------------------------------------------
# 🧠 智能 RAG 接口
# ----------------------------------------------------
@router.post("/rag_chat")
async def rag_chat(
    request: ChatRequest, 
    session: Session = Depends(get_session)
):
    user_question = request.message

    # === 第一阶段：意图识别与关键词提取 ===
    # 🔥 升级 Prompt：让 AI 联想更多相关词，提高命中率
    system_prompt_1 = """
    你是一个搜索专家。判断用户的输入是否需要查询旅游日记数据库。
    如果需要，请提取 **2-3 个最核心的搜索关键词**，用空格分隔。
    
    【技巧】：
    1. 去掉修饰语（"学校食堂" -> "食堂"）。
    2. 增加同义词（"好吃的" -> "美食 好吃"）。
    3. 越短越好，不要长句子。

    例如：
    用户："大家都喜欢去哪吃烤鸭？" -> 返回："烤鸭 鸭"
    用户："学校食堂的饭好吃吗" -> 返回："食堂 饭菜"
    用户："你好" -> 返回："NO_SEARCH"
    """
    
    try:
        response1 = await client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt_1},
                {"role": "user", "content": user_question}
            ],
            stream=False
        )
        keyword_str = response1.choices[0].message.content.strip()
        
        # === 第二阶段：分支处理 ===
        
        if "NO_SEARCH" in keyword_str:
            # 不需要查库，直接陪聊
            final_reply = await client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": user_question}]
            )
            return {"reply": final_reply.choices[0].message.content}
        
        else:
            # 需要查库
            # 1. 调用升级版工具查数据
            db_content = search_database_tool(session, keyword_str)
            
            # 2. 组装最终回答
            final_system_prompt = f"""
            你是一个基于数据库的智能导游。
            用户问："{user_question}"
            
            我通过关键词 "{keyword_str}" 检索到了以下相关日记：
            ================
            {db_content}
            ================
            
            请根据数据库内容回答用户。如果没找到相关内容，请礼貌告知。
            """
            
            response2 = await client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": final_system_prompt},
                    {"role": "user", "content": user_question}
                ]
            )
            return {"reply": response2.choices[0].message.content, "source": "已检索数据库"}

    except Exception as e:
        print