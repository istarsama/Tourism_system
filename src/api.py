"""
校园旅游系统后端入口。

职责：
- 应用生命周期管理（数据库初始化、地图加载、POI 同步）
- FastAPI 应用创建与中间件配置
- 路由注册（各业务域路由已拆分到 routers/ 子模块）
- 静态文件挂载

所有具体业务逻辑已迁移到：
- src/routers/  ← 路由层
- src/services/ ← 服务层
- src/schemas/  ← 请求/响应模型
"""

import os
import sys

# 把 src 目录加入 Python 搜索路径，方便各子模块互相导入
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger
from sqlmodel import Session

import auth
import diary
import upload
import ai
from database import init_db, engine
from poi_service import sync_campus_graph_to_poi
from services.map_service import load_and_set_graph
from utils import get_data_path

# 注册各业务路由
from routers.map import router as map_router, ensure_default_map_configs
from routers.navigation import router as navigation_router
from routers.spots import router as spots_router
from routers.xhs import router as xhs_router

# 向后兼容：部分测试直接通过 api.osm_service 访问实例并打 mock
from services.map_service import get_osm_service as _get_osm_service

# 延迟绑定，确保测试可以 patch api.osm_service.route_planning
class _OsmServiceProxy:
    """代理对象：将属性访问转发到服务层单例，允许测试直接 patch。"""
    def __getattr__(self, name):
        return getattr(_get_osm_service(), name)
    def __setattr__(self, name, value):
        if name.startswith("_"):
            super().__setattr__(name, value)
        else:
            setattr(_get_osm_service(), name, value)

osm_service = _OsmServiceProxy()


# ─────────────────────────────────────────────────
# 应用生命周期
# ─────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🔄 正在检查数据库表结构...")
    init_db()
    logger.info("✅ 数据库表检查完毕！")

    with Session(engine) as session:
        ensure_default_map_configs(session)

    try:
        path = get_data_path()
        graph = load_and_set_graph(path)
        logger.info("✅ 地图加载成功，包含 {} 个景点", len(graph.spots))
        with Session(engine) as session:
            stats = sync_campus_graph_to_poi(session, graph)
            logger.info("✅ POI 同步完成: {}", stats)
    except Exception as e:
        logger.error("❌ 地图加载失败: {}", e)

    yield

    logger.info("🛑 服务已关闭")


# ─────────────────────────────────────────────────
# 应用实例
# ─────────────────────────────────────────────────

app = FastAPI(title="校园旅游系统", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────
# 静态目录（必须在 API 路由之前挂载非根路径）
# ─────────────────────────────────────────────────

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/data", StaticFiles(directory="data"), name="data")

# ─────────────────────────────────────────────────
# 路由注册
# ─────────────────────────────────────────────────

app.include_router(auth.router)
app.include_router(diary.router)
app.include_router(upload.router)
app.include_router(ai.router)
app.include_router(spots_router)
app.include_router(map_router)
app.include_router(navigation_router)
app.include_router(xhs_router)


# ─────────────────────────────────────────────────
# 根路由
# ─────────────────────────────────────────────────

@app.get("/")
def read_root():
    return {"status": "ok", "message": "校园旅游系统后端正在运行"}


# ─────────────────────────────────────────────────
# 前端静态文件（必须放在所有 API 路由之后）
# ─────────────────────────────────────────────────

frontend_dist_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend-dist")
if os.path.isdir(frontend_dist_dir):
    app.mount("/", StaticFiles(directory=frontend_dist_dir, html=True), name="frontend")
    logger.info("✅ 已挂载前端构建产物目录: {}", frontend_dist_dir)
