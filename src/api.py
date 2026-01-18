import sys
import os
# 把当前文件所在的目录 (src) 加入到 Python 查找路径中，这样就能找到 auth, diary 等模块了
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
from contextlib import asynccontextmanager
# 导入我们自己写的模块
import auth               # 身份认证模块
import diary              # 日记模块 (刚才写的)
from models import CampusGraph
# 从 algorithms 导入两个核心函数
from algorithms import dijkstra_search, plan_multi_point_route
from utils import load_graph_from_json, get_data_path
import upload # 文件上传模块
import ai     # AI 助手模块
# 导入数据库初始化函数
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
# 【修改】导航请求模型
# 对应 PPT 需求：
# 1. 途经多点 [cite: 120] -> via_ids
# 2. 交通工具 [cite: 127] -> transport
class NavigateRequest(BaseModel):
    start_id: int
    # end_id 变为可选，因为如果是多点规划，可能只需提供 via_ids
    end_id: Optional[int] = None    
    
    # 【新增】途经点列表 (多点规划用)
    via_ids: List[int] = []         
    
    # 【新增】策略: 'dist'=最短距离, 'time'=最短时间(含拥挤度) [cite: 126]
    strategy: str = 'dist'          
    
    # 【新增】交通工具: 'walk'=步行, 'bike'=自行车 [cite: 127]
    transport: str = 'walk'         

class NavigateResponse(BaseModel):
    path_ids: List[int]
    path_names: List[str]
    total_cost: float
    cost_unit: str  # 告诉前端单位是 "米" 还是 "秒"

# --- 根目录测试 ---
@app.get("/")
def read_root():
    return {"status": "ok", "message": "校园旅游系统后端正在运行"}

# --- 导航接口 ---
@app.post("/navigate", response_model=NavigateResponse)
def navigate(request: NavigateRequest):
    """
    【智能导航接口】
    支持功能：
    1. A -> B 单点导航 (最短距离/最短时间)
    2. A -> B -> C -> D 多点连线规划 (TSP近似)
    3. 交通方式选择 (步行/自行车)
    """
    # 1. 安全检查：地图是否加载
    if not global_graph:
        raise HTTPException(status_code=500, detail="地图未初始化")
    
    path_ids = []
    cost = 0.0
    
    # 2. 分支逻辑处理
    
    # --- 情况 A: 多点规划 (如果不为空) [cite: 120] ---
    if request.via_ids:
        # 简单的错误检查：确保所有途经点都存在
        for vid in request.via_ids:
            if vid not in global_graph.spots:
                 raise HTTPException(status_code=404, detail=f"途经点 ID {vid} 不存在")
        
        # 调用我们刚才写的多点规划算法
        path_ids, cost = plan_multi_point_route(
            global_graph, 
            request.start_id, 
            request.via_ids, 
            request.strategy, 
            request.transport
        )
        
    # --- 情况 B: 单点导航 (A -> B) [cite: 119] ---
    elif request.end_id is not None:
        if request.end_id not in global_graph.spots:
            raise HTTPException(status_code=404, detail="终点不存在")
            
        # 调用基础 Dijkstra 算法
        path_ids, cost = dijkstra_search(
            global_graph, 
            request.start_id, 
            request.end_id, 
            request.strategy, 
            request.transport
        )
    
    # --- 情况 C: 参数错误 ---
    else:
        raise HTTPException(status_code=400, detail="必须提供 终点(end_id) 或 途经点列表(via_ids)")
    
    # 3. 结果处理
    if not path_ids:
        raise HTTPException(status_code=400, detail="无法规划路径（可能是孤岛节点或无法到达）")

    # 将 ID 转换为人类可读的景点名称
    path_names = [global_graph.get_spot_name(pid) for pid in path_ids]
    
    # 确定单位 (距离用米，时间用秒)
    unit = "米" if request.strategy == 'dist' else "秒"
    
    return {
        "path_ids": path_ids,
        "path_names": path_names,
        "total_cost": round(cost, 1), # 保留1位小数
        "cost_unit": unit
    }