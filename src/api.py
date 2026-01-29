import sys
import os
# 把当前文件所在的目录 (src) 加入到 Python 查找路径中，这样就能找到 auth, diary 等模块了
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from fastapi import FastAPI, APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from database import get_session
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
from contextlib import asynccontextmanager
from thefuzz import process  # 用于模糊搜索
# 导入我们自己写的模块
import auth               # 身份认证模块
import diary              # 日记模块 (刚才写的)
from models import CampusGraph, Spot
from crawler import XHSCrawler
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
# 1. 挂载静态文件目录 (非根路径的先挂载)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/data", StaticFiles(directory="data"), name="data")

# 2. 注册路由
app.include_router(auth.router)   # 用户登录注册
app.include_router(diary.router)  # 日记功能
app.include_router(upload.router) # <--- 3. 启用上传接口
app.include_router(ai.router)     # AI 助手
# ==========================================

# 【新增】地图查询接口
# 1. 获取所有景点 (用于前端下拉框)
@app.get("/spots/list")
def get_all_spots():
    if not global_graph:
        return []
    # 只返回 type='spot' 的景点，不返回路点
    return [spot for spot in global_graph.spots.values() if spot.type == 'spot']

# 2. 模糊搜索 (解决输入不准的问题)
@app.get("/spots/search")
def search_spots(query: str, limit: int = 5):
    """
    输入 "食堂" -> 返回 [{"name": "学生食堂", ...}, ...]
    """
    if not global_graph:
        return []

    # 1. 拿到所有景点名字 map: {"学生食堂": 44, "教工食堂": 19}
    spot_map = {s.name: s.id for s in global_graph.spots.values() if s.type == 'spot'}
    
    if not spot_map:
        return []

    # 2. 模糊匹配
    matches = process.extract(query, spot_map.keys(), limit=limit)
    
    results = []
    for name, score in matches:
        if score > 40:  # 匹配度大于 40 分才显示
            spot_id = spot_map[name]
            spot_obj = global_graph.spots[spot_id]
            results.append({
                "id": spot_id,
                "name": name,
                "score": score,
                "x": spot_obj.x, # 把坐标也带上，方便前端定位
                "y": spot_obj.y
            })
            
    return results

# 【新增】集成小红书爬虫 + AI 路线规划接口
class XHSPlanRequest(BaseModel):
    keyword: str
    days: int = 1

@app.post("/plan/xhs_trip")
async def plan_xhs_trip(request: XHSPlanRequest, session: Session = Depends(get_session)):
    """
    1. 调用爬虫抓取小红书笔记
    2. AI 分析笔记提取景点
    3. (可选) 生成路线建议
    """
    print(f"🚀 开始执行小红书旅游规划: {request.keyword}")
    
    # 1. 爬取数据
    crawler = XHSCrawler()
    # 注意：如果没装 Node.js，这里会返回模拟数据
    notes = crawler.search_notes(request.keyword, limit=10)
    
    if not notes:
        return {"msg": "未找到相关笔记", "spots": []}
    
    # 2. 尝试在数据库里创建一个“临时景点”来挂载这些日记
    # 先查有没有叫这个名字的景点
    spot = session.exec(select(Spot).where(Spot.name == request.keyword)).first()
    if not spot:
        # 创建一个虚拟景点 (坐标 0,0)
        spot = Spot(id=9999 + len(request.keyword), name=request.keyword, x=0, y=0, desc="网络搜索生成的虚拟景点")
        # 注意：这里我们可能需要处理 ID 冲突，简单起见先这样
        # 更好的做法是让 ID 自增，但 Spot 模型里 ID 不是自增主键。
        # 这里为了演示，我们假设 ID 不会冲突
    
    # 3. 保存日记到数据库 (关联到这个景点)
    # 假设当前用户是管理员 (ID=1)
    saved_count = crawler.save_to_db(notes, session, user_id=1, spot_id=spot.id)
    
    # 4. AI 分析文本，提取具体的子景点
    all_text = "\n".join([n['desc'] for n in notes])
    extracted_spots = await ai.extract_spots_from_text(all_text)
    
    return {
        "status": "success",
        "msg": f"成功抓取 {len(notes)} 条笔记，并存入数据库。",
        "saved_diaries": saved_count,
        "ai_extracted_spots": extracted_spots,
        "notes_preview": notes[:2]
    }

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
    path_coords: List[List[float]] # ➕【新增这一行】返回像素坐标供前端画线
    total_cost: float
    cost_unit: str  # 告诉前端单位是 "米" 还是 "秒"

# --- 根目录测试 ---
@app.get("/")
def read_root():
    return {"status": "ok", "message": "校园旅游系统后端正在运行"}

@app.get("/graph")
def get_graph():
    """
    返回前端渲染地图所需的节点和边数据
    """
    if not global_graph:
        raise HTTPException(status_code=500, detail="地图数据未加载")
    
    # 1. 提取所有景点节点
    # vars(obj) 可以把对象转成字典 {id:1, name:"...", x:10, y:20...}
    nodes_data = [vars(spot) for spot in global_graph.spots.values()]
    
    # 2. 提取所有边 (去重)
    # 因为是无向图逻辑，A->B 和 B->A 在算法里都有，但画图只需要一份
    edges_data = []
    seen_edges = set()
    
    for u_id, roads in global_graph.adj.items():
        for road in roads:
            # 使用排序后的 tuple 作为唯一标识 (1, 2) == (2, 1)
            pair = tuple(sorted((road.u, road.v)))
            if pair not in seen_edges:
                edges_data.append({
                    "u": road.u,
                    "v": road.v,
                    "distance": road.distance,
                    # 如果前端需要显示拥挤度或类型，可以在这里加
                })
                seen_edges.add(pair)
                
    return {"nodes": nodes_data, "edges": edges_data}

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

    # ➕ 提取路径上每个点的像素坐标 [x, y]，供前端在图片上画线
    path_coords = []
    for pid in path_ids:
        # 这里的 global_graph 就是你加载进内存的“地图数据”
        if pid in global_graph.spots:
            spot = global_graph.spots[pid]
            path_coords.append([spot.x, spot.y])
        else:
            path_coords.append([0, 0]) # 防止报错
    
    # 确定单位 (距离用米，时间用秒)
    unit = "米" if request.strategy == 'dist' else "秒"
    
    return {
        "path_ids": path_ids,
        "path_names": path_names,
        "path_coords": path_coords,  # 返回坐标数据
        "total_cost": round(cost, 1), # 保留1位小数
        "cost_unit": unit
    }
# ==========================================
# 【重要】前端静态文件挂载 - 必须放在所有 API 路由之后
# 这样 API 路由优先匹配，未匹配的请求才会走静态文件
# ==========================================
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")