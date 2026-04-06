import sys
import os
from datetime import datetime
from time import perf_counter
from datetime import datetime
# 把当前文件所在的目录 (src) 加入到 Python 查找路径中，这样就能找到 auth, diary 等模块了
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from fastapi import FastAPI, APIRouter, HTTPException, Depends
from fastapi import Query
from sqlmodel import Session, select
from sqlalchemy import func
from database import get_session
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
from contextlib import asynccontextmanager
from loguru import logger
from thefuzz import process  # 用于模糊搜索
# 导入我们自己写的模块
import auth               # 身份认证模块
import diary              # 日记模块 (刚才写的)
from models import CampusGraph, NationalSpot, MapConfig, Diary, NationalSpotXHSNote
from crawler import XHSCrawler
from osm_service import OSMService
from poi_service import sync_campus_graph_to_poi, get_or_create_virtual_poi
# 从 algorithms 导入两个核心函数
from algorithms import dijkstra_search, plan_multi_point_route
from utils import load_graph_from_json, get_data_path
import upload # 文件上传模块
import ai     # AI 助手模块
# 导入数据库初始化函数
from database import init_db, engine

# 全局变量：用来在内存里存地图数据
global_graph: Optional[CampusGraph] = None
osm_service = OSMService()

DEFAULT_MAP_CONFIGS = {
    "campus": {
        "center_lat": 39.9629,
        "center_lng": 116.3520,
        "zoom_level": 16,
        "map_provider": "campus_canvas",
    },
    "national": {
        "center_lat": 35.8617,
        "center_lng": 104.1954,
        "zoom_level": 5,
        "map_provider": "osm",
    },
}

MAP_RENDERING_HINTS = {
    "campus": {
        "supports_slippy_map": False,
        "coordinate_system": "campus_pixel",
        "tile_layer": None,
    },
    "national": {
        "supports_slippy_map": True,
        "coordinate_system": "wgs84",
        "tile_layer": {
            "tile_url": "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
            "attribution": "&copy; OpenStreetMap contributors",
            "min_zoom": 3,
            "max_zoom": 19,
            "subdomains": ["a", "b", "c"],
            "usage_tier": "demo",
            "usage_note": "仅建议开发或课堂演示环境直连公开 OSM 瓦片；生产环境请替换为自建或商用瓦片服务。",
            "requires_backend_proxy": False,
        },
    },
}


def _ensure_default_map_configs(session: Session) -> None:
    created = False
    for scope, cfg in DEFAULT_MAP_CONFIGS.items():
        existing = session.exec(
            select(MapConfig).where(MapConfig.scope == scope)
        ).first()
        if existing:
            continue
        session.add(MapConfig(scope=scope, **cfg))
        created = True
    if created:
        session.commit()
        logger.info("✅ 已初始化默认地图配置数据")

# --- 生命周期管理器 ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    这个函数会在服务器 启动前 和 关闭后 运行
    """
    # 【启动阶段】
    logger.info("🔄 正在检查数据库表结构...")
    init_db()  # <--- 关键修复：如果没有表，这里会自动创建！
    logger.info("✅ 数据库表检查完毕！")
    with Session(engine) as session:
        _ensure_default_map_configs(session)

    # 加载地图数据
    global global_graph
    try:
        path = get_data_path()
        global_graph = load_graph_from_json(path)
        logger.info(f"✅ 地图加载成功，包含 {len(global_graph.spots)} 个景点")
        with Session(engine) as session:
            stats = sync_campus_graph_to_poi(session, global_graph)
            logger.info(f"✅ POI 同步完成: {stats}")
    except Exception as e:
        logger.error(f"❌ 地图加载失败: {e}")
    
    yield  # 程序在这里暂停，等待用户请求...
    
    # 【关闭阶段】
    logger.info("🛑 服务已关闭")

# --- 创建 APP ---
app = FastAPI(title="校园旅游系统", lifespan=lifespan)

# --- 配置跨域 (允许前端网页访问) ---
app.add_middleware(
    CORSMiddleware,
    # 允许哪些前端源来访问？"*" 代表允许所有。
    # 在公司生产环境中，为了安全，通常会严格写成 ["https://your-frontend-domain.com"]
    allow_origins=["*"],  
    
    # 是否允许前端发送 Cookie、Token 等用户凭证？
    allow_credentials=True, 
    
    # 允许前端使用哪些 HTTP 方法？(GET, POST, PUT, DELETE 等) "*" 代表全放行。
    allow_methods=["*"],
    
    # 允许前端在请求里带上哪些自定义的请求头？"*" 代表全放行。
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
def search_spots(
    query: str,
    limit: int = Query(default=5, ge=1, le=20),
    scope: str = Query(default="campus", pattern="^(campus|national)$"),
    city: Optional[str] = None,
    session: Session = Depends(get_session),
):
    """
    输入 "食堂" -> 返回 [{"name": "学生食堂", ...}, ...]
    """
    if scope == "campus":
        if not global_graph:
            return []

        # 1. 拿到所有景点名字 map: {"学生食堂": 44, "教工食堂": 19}
        spot_map = {s.name: s.id for s in global_graph.spots.values() if s.type == "spot"}
        if not spot_map:
            return []

        # 2. 模糊匹配
        matches = process.extract(query, spot_map.keys(), limit=limit)
        results = []
        for name, score in matches:
            if score > 40:  # 匹配度大于 40 分才显示
                spot_id = spot_map[name]
                spot_obj = global_graph.spots[spot_id]
                results.append(
                    {
                        "id": spot_id,
                        "name": name,
                        "score": score,
                        "x": spot_obj.x,  # 把坐标也带上，方便前端定位
                        "y": spot_obj.y,
                        "scope": "campus",
                    }
                )
        return results

    query_stmt = select(NationalSpot).where(NationalSpot.is_active == True)
    if city:
        query_stmt = query_stmt.where(NationalSpot.city == city)
    national_spots = session.exec(query_stmt).all()
    if not national_spots:
        return []

    label_to_spot = {}
    for spot in national_spots:
        label = f"{spot.name}({spot.city})"
        label_to_spot[label] = spot

    matches = process.extract(query, label_to_spot.keys(), limit=limit)
    results = []
    for label, score in matches:
        if score <= 40:
            continue
        spot = label_to_spot[label]
        results.append(
            {
                "id": spot.id,
                "name": spot.name,
                "city": spot.city,
                "type": spot.type,
                "score": score,
                "latitude": spot.latitude,
                "longitude": spot.longitude,
                "xhs_note_count": spot.xhs_note_count,
                "xhs_fetch_status": spot.xhs_fetch_status,
                "xhs_cookie_needs_refresh": spot.xhs_cookie_needs_refresh,
                "scope": "national",
            }
        )
    return results

# 【新增】集成小红书爬虫 + AI 路线规划接口
class XHSPlanRequest(BaseModel):
    keyword: str
    days: int = 1


class TileLayerResponse(BaseModel):
    tile_url: str
    attribution: str
    min_zoom: int
    max_zoom: int
    subdomains: List[str]
    usage_tier: str
    usage_note: str
    requires_backend_proxy: bool


class MapModeResponse(BaseModel):
    scope: str
    center_lat: Optional[float]
    center_lng: Optional[float]
    zoom_level: int
    map_provider: str
    data_source: str
    supports_slippy_map: bool
    coordinate_system: str
    tile_layer: Optional[TileLayerResponse]


class NationalSpotXHSPreviewResponse(BaseModel):
    note_id: str
    title: str
    content_preview: str
    thumbnail_url: Optional[str]
    xhs_url: str
    author_name: Optional[str]
    author_id: Optional[str]
    likes: int


class NationalSpotMapResponse(BaseModel):
    id: int
    name: str
    type: str
    latitude: float
    longitude: float
    description: Optional[str]
    city: str
    province: Optional[str]
    flower_type: Optional[str]
    best_season: Optional[str]
    rating: float
    diary_count: int
    diary_api: str
    xhs_query: Optional[str]
    xhs_note_count: int
    xhs_fetch_status: str
    xhs_fetch_message: Optional[str]
    xhs_cookie_needs_refresh: bool
    xhs_last_fetched_at: Optional[datetime]
    xhs_notes_preview: List[NationalSpotXHSPreviewResponse]

@app.post("/plan/xhs_trip")
async def plan_xhs_trip(request: XHSPlanRequest, session: Session = Depends(get_session)):
    """
    1. 调用爬虫抓取小红书笔记
    2. AI 分析笔记提取景点
    3. (可选) 生成路线建议
    """
    logger.info(f"🚀 开始执行小红书旅游规划: {request.keyword}")
    
    # 1. 爬取数据
    crawler = XHSCrawler()
    # 注意：如果没装 Node.js，这里会返回模拟数据
    notes = crawler.search_notes(request.keyword, limit=10)
    
    if not notes:
        return {"msg": "未找到相关笔记", "spots": []}
    
    # 2. 从统一 POI 中查找或创建一个虚拟景点
    poi = get_or_create_virtual_poi(
        session,
        request.keyword,
        description="网络搜索生成的虚拟景点",
    )
    if poi.legacy_spot_id is None:
        raise HTTPException(status_code=500, detail="虚拟景点创建成功但未生成 legacy_spot_id")
    
    # 3. 保存日记到数据库 (关联到这个景点)
    # 假设当前用户是管理员 (ID=1)
    saved_count = crawler.save_to_db(notes, session, user_id=1, spot_id=poi.legacy_spot_id)
    
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


@app.get("/map/mode", response_model=MapModeResponse)
def get_map_mode(
    scope: str = Query(default="campus", pattern="^(campus|national)$"),
    session: Session = Depends(get_session),
):
    config = session.exec(select(MapConfig).where(MapConfig.scope == scope)).first()
    if not config:
        default_cfg = DEFAULT_MAP_CONFIGS[scope]
        config = MapConfig(scope=scope, **default_cfg)
        session.add(config)
        session.commit()
        session.refresh(config)

    render_hint = MAP_RENDERING_HINTS[scope]
    return {
        "scope": config.scope,
        "center_lat": config.center_lat,
        "center_lng": config.center_lng,
        "zoom_level": config.zoom_level,
        "map_provider": config.map_provider,
        "data_source": "campus_graph" if scope == "campus" else "national_spot",
        "supports_slippy_map": render_hint["supports_slippy_map"],
        "coordinate_system": render_hint["coordinate_system"],
        "tile_layer": render_hint["tile_layer"],
    }


@app.get("/map/campus-graph")
def get_campus_graph():
    return get_graph()


@app.get("/map/national-spots", response_model=List[NationalSpotMapResponse])
def get_national_spots(
    city: Optional[str] = None,
    spot_type: Optional[str] = Query(default=None, alias="type"),
    limit: int = Query(default=200, ge=1, le=500),
    session: Session = Depends(get_session),
):
    """
    返回全国景点地图点位及其小红书预览元数据。

    这里保持原有 diary_count / diary_api 字段不变，并以新增字段的方式扩展，
    这样现有 OSM 前端链路不会被破坏，后续点击景点即可直接展示帖子缩略图与跳转链接。
    """
    query = select(NationalSpot).where(NationalSpot.is_active == True)
    if city:
        query = query.where(NationalSpot.city == city)
    if spot_type:
        query = query.where(NationalSpot.type == spot_type)

    spots = session.exec(
        query.order_by(NationalSpot.rating.desc(), NationalSpot.name).limit(limit)
    ).all()
    if not spots:
        return []

    spot_ids = [spot.id for spot in spots if spot.id is not None]
    diary_count_map: dict[int, int] = {}
    if spot_ids:
        rows = session.exec(
            select(Diary.national_spot_id, func.count(Diary.id))
            .where(
                Diary.scope == "national",
                Diary.national_spot_id.in_(spot_ids),
            )
            .group_by(Diary.national_spot_id)
        ).all()
        diary_count_map = {
            int(national_spot_id): int(count)
            for national_spot_id, count in rows
            if national_spot_id is not None
        }

    note_preview_map: dict[int, list[dict]] = {}
    if spot_ids:
        preview_rows = session.exec(
            select(NationalSpotXHSNote)
            .where(NationalSpotXHSNote.national_spot_id.in_(spot_ids))
            .order_by(
                NationalSpotXHSNote.national_spot_id,
                NationalSpotXHSNote.rank_order,
                NationalSpotXHSNote.id,
            )
        ).all()
        for preview in preview_rows:
            note_preview_map.setdefault(preview.national_spot_id, []).append(
                {
                    "note_id": preview.xhs_note_id,
                    "title": preview.title,
                    "content_preview": preview.content_preview,
                    "thumbnail_url": preview.thumbnail_url,
                    "xhs_url": preview.xhs_url,
                    "author_name": preview.author_name,
                    "author_id": preview.author_id,
                    "likes": preview.liked_count,
                }
            )

    return [
        {
            "id": spot.id,
            "name": spot.name,
            "type": spot.type,
            "latitude": spot.latitude,
            "longitude": spot.longitude,
            "description": spot.description,
            "city": spot.city,
            "province": spot.province,
            "flower_type": spot.flower_type,
            "best_season": spot.best_season,
            "rating": spot.rating,
            "diary_count": diary_count_map.get(spot.id, 0),
            "diary_api": f"/diaries/spot/{spot.id}?scope=national",
            "xhs_query": spot.xhs_query,
            "xhs_note_count": spot.xhs_note_count,
            "xhs_fetch_status": spot.xhs_fetch_status,
            "xhs_fetch_message": spot.xhs_fetch_message,
            "xhs_cookie_needs_refresh": spot.xhs_cookie_needs_refresh,
            "xhs_last_fetched_at": spot.xhs_last_fetched_at,
            "xhs_notes_preview": note_preview_map.get(spot.id, []),
        }
        for spot in spots
    ]

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


class OSMNavigateRequest(BaseModel):
    start_spot_id: int
    end_spot_id: int
    transport: str = "walk"


class OSMNavigateResponse(BaseModel):
    city: str
    transport: str
    start_spot_id: int
    end_spot_id: int
    node_ids: List[int]
    path_coords: List[List[float]]
    total_distance_m: float
    segment_count: int
    segment_distances_m: List[float]
    estimated_duration_s: float

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


@app.post("/navigate/osm", response_model=OSMNavigateResponse)
def navigate_osm(request: OSMNavigateRequest, session: Session = Depends(get_session)):
    started_at = perf_counter()
    logger.info(
        "收到 OSM 导航请求 start_spot_id={} end_spot_id={} transport={}",
        request.start_spot_id,
        request.end_spot_id,
        request.transport,
    )
    if request.transport not in {"walk", "bike"}:
        raise HTTPException(status_code=400, detail="transport 仅支持 'walk' 或 'bike'")

    start_spot = session.get(NationalSpot, request.start_spot_id)
    if not start_spot or not start_spot.is_active:
        raise HTTPException(status_code=404, detail="起点全国景点不存在")

    end_spot = session.get(NationalSpot, request.end_spot_id)
    if not end_spot or not end_spot.is_active:
        raise HTTPException(status_code=404, detail="终点全国景点不存在")

    if start_spot.city != end_spot.city:
        raise HTTPException(status_code=400, detail="当前仅支持同城市景点之间的 OSM 导航")

    try:
        result = osm_service.route_planning(
            city=start_spot.city,
            start_lat=start_spot.latitude,
            start_lng=start_spot.longitude,
            end_lat=end_spot.latitude,
            end_lng=end_spot.longitude,
            transport=request.transport,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    segment_distances_m = [float(distance) for distance in result.get("segment_distances_m", [])]
    segment_count = int(result.get("segment_count", len(segment_distances_m)))
    estimated_duration_s = float(result.get("estimated_duration_s", 0.0))
    response = {
        "city": result["city"],
        "transport": result["transport"],
        "start_spot_id": request.start_spot_id,
        "end_spot_id": request.end_spot_id,
        "node_ids": result["node_ids"],
        "path_coords": result["path_coords"],
        "total_distance_m": result["total_distance_m"],
        "segment_count": segment_count,
        "segment_distances_m": segment_distances_m,
        "estimated_duration_s": estimated_duration_s,
    }
    elapsed_ms = (perf_counter() - started_at) * 1000
    logger.info(
        "OSM 导航完成 city={} nodes={} segments={} distance={}m eta={}s elapsed_ms={:.2f}",
        response["city"],
        len(response["node_ids"]),
        response["segment_count"],
        response["total_distance_m"],
        response["estimated_duration_s"],
        elapsed_ms,
    )
    return response
# ==========================================
# 【重要】前端静态文件挂载 - 必须放在所有 API 路由之后
# 这样 API 路由优先匹配，未匹配的请求才会走静态文件
# ==========================================
frontend_dist_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend-dist")
if os.path.isdir(frontend_dist_dir):
    app.mount("/", StaticFiles(directory=frontend_dist_dir, html=True), name="frontend")
    logger.info("✅ 已挂载前端构建产物目录: {}", frontend_dist_dir)
else:
    logger.warning("⚠️ 未找到 frontend-dist，当前使用前后端分离开发模式（请运行 frontend\\npm run dev）")
