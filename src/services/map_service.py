"""
地图服务层：管理校园图内存状态与 OSM 路网服务实例。

设计原则：
- global_graph 和 osm_service 是应用级单例，通过此模块统一访问。
- 路由层通过 get_graph() / get_osm_service() 获取，不直接引用模块全局变量。
- 这样可以在测试中方便替换 graph，也避免循环导入。
"""

from typing import Optional
from loguru import logger

from models import CampusGraph
from osm_service import OSMService

# 应用级单例
_global_graph: Optional[CampusGraph] = None
_osm_service: Optional[OSMService] = None


def get_graph() -> Optional[CampusGraph]:
    return _global_graph


def set_graph(graph: CampusGraph) -> None:
    global _global_graph
    _global_graph = graph
    logger.info("MapService: 图已更新，共 {} 个节点", len(graph.spots))


def get_osm_service() -> OSMService:
    global _osm_service
    if _osm_service is None:
        _osm_service = OSMService()
    return _osm_service


def load_and_set_graph(path: str) -> CampusGraph:
    """从 JSON 文件加载地图并写入全局状态，返回加载后的图对象。"""
    from utils import load_graph_from_json

    graph = load_graph_from_json(path)
    set_graph(graph)
    return graph
