from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

# 导入复用的模块
from models import CampusGraph
from algorithms import dijkstra_search
from utils import load_graph_from_json, get_data_path

# --- 1. 定义数据格式 ---
class NavigateRequest(BaseModel):
    start_id: int
    end_id: int
    strategy: str = 'dist'

class NavigateResponse(BaseModel):
    path_ids: List[int]
    path_names: List[str]
    total_cost: float

# --- 2. 初始化 App ---
app = FastAPI(title="校园旅游系统")

# 允许跨域 (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 3. 全局变量 & 启动加载 ---
global_graph: Optional[CampusGraph] = None

@app.on_event("startup")
def startup_event():
    global global_graph
    try:
        path = get_data_path()
        global_graph = load_graph_from_json(path)
        print(f"✅ 地图加载成功，包含 {len(global_graph.spots)} 个景点")
    except Exception as e:
        print(f"❌ 启动失败: {e}")

# --- 4. 接口定义 ---

@app.get("/")
def read_root():
    return {"status": "ok"}

# 【修改点】前端 app.js 请求的是 /graph，而且需要 edges
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
    # 遍历邻接表，为了防止前端重复画线，我们只取 u < v 的边（因为是无向图）
    for u_id, roads in global_graph.adj.items():
        for road in roads:
            if road.u < road.v:  # 简单去重
                edges_data.append({
                    "u": road.u,
                    "v": road.v,
                    "dist": road.distance,
                    "type": road.type, # 注意：确保 models.py 里 Road 类有 type 属性
                    "crowding": road.crowding
                })

    # 返回前端需要的结构
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