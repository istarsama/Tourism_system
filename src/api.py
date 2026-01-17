from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

# 导入我们可以复用的模块
from models import CampusGraph
from algorithms import dijkstra_search
from utils import load_graph_from_json, get_data_path

# --- 1. 定义数据交互格式 (Schema) ---
# 使用 Pydantic 来验证前端发来的数据是否合法，这能省去很多 if-else 检查

class NavigateRequest(BaseModel):
    start_id: int
    end_id: int
    strategy: str = 'dist' # 默认按距离，也可以传 'time'

class NavigateResponse(BaseModel):
    path_ids: List[int]
    path_names: List[str]
    total_cost: float

# --- 2. 初始化 App ---
app = FastAPI(
    title="校园个性化旅游系统 API",
    description="基于大模型的数据结构课程设计后端接口",
    version="1.0.0"
)

# 允许跨域 (CORS) - 这一步非常重要！
# 否则你的前端同学（运行在 localhost:5173 等端口）无法访问你的后端（localhost:8000）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发阶段允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 3. 全局变量：地图 ---
# 我们不希望每次请求都重新读文件，那样太慢。
# 所以我们在启动时读一次，存到内存里。
global_graph: Optional[CampusGraph] = None

@app.on_event("startup")
def startup_event():
    global global_graph
    try:
        path = get_data_path()
        global_graph = load_graph_from_json(path)
        print(f"✅ API 服务启动成功，地图已加载。包含 {len(global_graph.spots)} 个景点。")
    except Exception as e:
        print(f"❌ 启动失败: {e}")

# --- 4. 编写接口 ---

@app.get("/")
def read_root():
    return {"message": "Welcome to Tourism System API"}

@app.get("/spots")
def get_all_spots():
    """获取所有景点信息（前端画地图用）"""
    if not global_graph:
        raise HTTPException(status_code=500, detail="地图未初始化")
    
    # 将字典转为列表返回
    # 注意：这里直接返回对象可能无法序列化，最好转成字典列表
    spots_data = []
    for spot in global_graph.spots.values():
        spots_data.append({
            "id": spot.id,
            "name": spot.name,
            "category": spot.category,
            "x": spot.x,
            "y": spot.y,
            "desc": spot.desc
        })
    return spots_data

@app.post("/navigate", response_model=NavigateResponse)
def navigate(request: NavigateRequest):
    """
    路径规划接口
    输入: {"start_id": 1, "end_id": 3, "strategy": "dist"}
    输出: 路径和消耗
    """
    if not global_graph:
        raise HTTPException(status_code=500, detail="地图未初始化")
    
    # 检查ID是否存在
    if request.start_id not in global_graph.spots or request.end_id not in global_graph.spots:
        raise HTTPException(status_code=404, detail="起点或终点ID不存在")

    # 调用你的核心算法！
    path_ids, cost = dijkstra_search(
        global_graph, 
        request.start_id, 
        request.end_id, 
        criterion=request.strategy
    )
    
    if not path_ids:
        raise HTTPException(status_code=400, detail="无法到达目的地")
        
    # 获取名称列表
    path_names = [global_graph.get_spot_name(pid) for pid in path_ids]
    
    return {
        "path_ids": path_ids,
        "path_names": path_names,
        "total_cost": cost
    }