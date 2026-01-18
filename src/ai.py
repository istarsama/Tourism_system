### ---基于deepseek--- ###
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from openai import AsyncOpenAI  # 导入用于连接大模型的工具

# 创建路由器
router = APIRouter(prefix="/ai", tags=["AI 智能助手"])

# ==========================================
# 🔑 配置区域 (要把你的 Key 填在这里)
# ==========================================
# 去 DeepSeek 官网申请的 API Key
# 格式通常是: sk-xxxxxxxxxxxxxxxxxxxx
DEEPSEEK_API_KEY = "*************" 

# DeepSeek 的官方接口地址
DEEPSEEK_BASE_URL = "https://api.deepseek.com"

# 初始化客户端
client = AsyncOpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)

# ==========================================
# 数据模型
# ==========================================
class ChatRequest(BaseModel):
    message: str  # 用户发来的问题

class PolishRequest(BaseModel):
    content: str  # 需要润色的日记草稿

# ==========================================
# 接口实现
# ==========================================

@router.post("/chat")
async def chat_with_ai(request: ChatRequest):
    """
    【智能导游聊天接口】
    用户问什么，DeepSeek 答什么。
    """
    try:
        # 调用 DeepSeek 模型
        response = await client.chat.completions.create(
            model="deepseek-chat",  # 指定模型名称
            messages=[
                # system: 给 AI 的人设，告诉它它是谁
                {"role": "system", "content": "你是一个校园旅游助手，非常了解北京邮电大学的景点。请用幽默风趣的口吻回答学生的问题。"},
                # user: 用户的问题
                {"role": "user", "content": request.message}
            ],
            stream=False
        )
        
        # 提取 AI 的回复内容
        ai_reply = response.choices[0].message.content
        return {"reply": ai_reply}

    except Exception as e:
        print(f"❌ AI 调用失败: {e}")
        # 如果报错（比如 Key 不对，或者没钱了），返回错误信息
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/polish")
async def polish_diary(request: PolishRequest):
    """
    【日记润色接口】
    帮你把大白话变成优美的散文。
    """
    try:
        response = await client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是一个文学大师。请帮我润色这段旅游日记，使其文笔优美、情感真挚，但不要改变原意。"},
                {"role": "user", "content": request.content}
            ],
            stream=False
        )
        polished_content = response.choices[0].message.content
        return {"original": request.content, "polished": polished_content}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))