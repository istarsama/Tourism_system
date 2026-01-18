from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
from contextlib import asynccontextmanager

# 1. 导入我们自己写的模块
import auth               # 身份认证模块
import diary              # 日记模块 (刚才写的)
from models import CampusGraph
from algorithms import dijkstra_search
from utils import load_graph_from_json, get_data_path
import upload # 文件上传模块
import ai     # AI 助手模块

# 2. 关键修复：导入数据库初始化函数
from database import init_db 

# 全局变量：用来在内存里存地图数据
global_graph: Optional[CampusGraph] = None

# --- 生命周期管理器 ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    这个函数会在服务器 启动前 和 关闭后 运行
    """
    # 【启动阶段】
    print("🔄 正在检查数据库表结构...")
    init_db()  # <--- 关键修复：如果没有表，这里会自动创建！
    print("✅ 数据库表检查完毕！")

    # 加载地图数据
    global global_graph
    try:
        path = get_data_path()
        global_graph = load_graph_from_json(path)
        print(f"✅ 地图加载成功，包含 {len(global_graph.spots)} 个景点")
    except Exception as e:
        print(f"❌ 地图加载失败: {e}")
    
    yield  # 程序在这里暂停，等待用户请求...
    
    # 【关闭阶段】
    print("🛑 服务已关闭")

# --- 创建 APP ---
app = FastAPI(title="校园旅游系统", lifespan=lifespan)

# --- 配置跨域 (允许前端网页访问) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 挂载路由 (把各个模块的接口装进来) ---
# ==========================================
# 1. 挂载静态文件目录
# 意思就是：当用户访问 http://.../uploads/xxx.jpg 时，
# FastAPI 会自动去项目根目录下的 'uploads' 文件夹里找对应的文件给我们看。
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# 2. 注册路由
app.include_router(auth.router)   # 用户登录注册
app.include_router(diary.router)  # 日记功能
app.include_router(upload.router) # <--- 3. 启用上传接口
app.include_router(ai.router)     # AI 助手
# ==========================================


# --- 定义导航请求的数据格式 ---
class NavigateRequest(BaseModel):
    start_id: int
    end_id: int
    strategy: str = 'dist' # 策略：dist=最短距离, time=最短时间

class NavigateResponse(BaseModel):
    path_ids: List[int]    # 路径上的点ID
    path_names: List[str]  # 路径上的点名称
    total_cost: float      # 总开销

# --- 根目录测试 ---
@app.get("/")
def read_root():
    return {"status": "ok", "message": "校园旅游系统后端正在运行"}

# --- 导航接口 ---
@app.post("/navigate", response_model=NavigateResponse)
def navigate(request: NavigateRequest):
    """
    路径规划接口：计算两个点之间的最优路径
    """
    if not global_graph:
        raise HTTPException(status_code=500, detail="地图未初始化")
    
    # 检查起终点是否存在
    if request.start_id not in global_graph.spots or request.end_id not in global_graph.spots:
        raise HTTPException(status_code=404, detail="起点或终点ID不存在")

    # 调用算法模块 (Dijkstra)
    path_ids, cost = dijkstra_search(
        global_graph, 
        request.start_id, 
        request.end_id, 
        criterion=request.strategy
    )
    
    if not path_ids:
        raise HTTPException(status_code=400, detail="无法到达目的地")
        
    # 把 ID 翻译成 中文名
    path_names = [global_graph.get_spot_name(pid) for pid in path_ids]
    
    return {
        "path_ids": path_ids,
        "path_names": path_names,
        "total_cost": cost
    }