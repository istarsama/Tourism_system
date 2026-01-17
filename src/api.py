from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from contextlib import asynccontextmanager # 1. 导入生命周期管理

# 导入复用的模块
import auth # 导入认证路由器
from models import CampusGraph
from algorithms import dijkstra_search
from utils import load_graph_from_json, get_data_path
# 记事本
import diary # <--- 新增导入

# --- 1. 全局变量 & 生命周期定义 (必须在 app 创建之前) ---
global_graph: Optional[CampusGraph] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 【启动时运行】
    global global_graph
    try:
        path = get_data_path()
        global_graph = load_graph_from_json(path)
        print(f"✅ 地图加载成功，包含 {len(global_graph.spots)} 个景点")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
    
    yield  # 程序暂停在这里等待请求
    
    # 【关闭时运行】
    print("🛑 服务已关闭")

# --- 2. 初始化 App (只创建这一次！) ---
app = FastAPI(title="校园旅游系统", lifespan=lifespan)

# --- 3. 配置 App (中间件 & 路由) ---

# 允许跨域 (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载 Auth 路由
app.include_router(auth.router)
app.include_router(diary.router) # <--- 新增挂载

# --- 4. 定义数据格式 ---
class NavigateRequest(BaseModel):
    start_id: int
    end_id: int
    strategy: str = 'dist'

class NavigateResponse(BaseModel):
    path_ids: List[int]
    path_names: List[str]
    total_cost: float

# --- 5. 接口定义 ---

@app.get("/")
def read_root():
    return {"status": "ok"}

@app.get("/graph")
def get_graph_data():
    """获取完整的地图数据（节点+边），供前端绘图"""
    if not global_graph:
        raise HTTPException(status_code=500, detail="地图未初始化")
    
    # 1. 整理节点数据
    nodes_data = []
    for spot in global_graph.spots.values():
        nodes_data.append({
            "id": spot.id,
            "name": spot.name,
            "category": spot.category,
            "x": spot.x,
            "y": spot.y,
            "desc": spot.desc
        })

    # 2. 整理边数据
    edges_data = []
    for u_id, roads in global_graph.adj.items():
        for road in roads:
            if road.u < road.v:  # 简单去重
                edges_data.append({
                    "u": road.u,
                    "v": road.v,
                    "dist": road.distance,
                    "type": road.type, 
                    "crowding": road.crowding
                })

    return {
        "nodes": nodes_data,
        "edges": edges_data
    }

@app.post("/navigate", response_model=NavigateResponse)
def navigate(request: NavigateRequest):
    """路径规划接口"""
    if not global_graph:
        raise HTTPException(status_code=500, detail="地图未初始化")
    
    if request.start_id not in global_graph.spots or request.end_id not in global_graph.spots:
        raise HTTPException(status_code=404, detail="ID不存在")

    path_ids, cost = dijkstra_search(
        global_graph, 
        request.start_id, 
        request.end_id, 
        criterion=request.strategy
    )
    
    if not path_ids:
        raise HTTPException(status_code=400, detail="无法到达目的地")
        
    path_names = [global_graph.get_spot_name(pid) for pid in path_ids]
    
    return {
        "path_ids": path_ids,
        "path_names": path_names,
        "total_cost": cost
    }