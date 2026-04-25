"""导航相关请求/响应 Pydantic 模型。"""

from typing import List, Optional

from pydantic import BaseModel


class NavigateRequest(BaseModel):
    start_id: int
    end_id: Optional[int] = None
    via_ids: List[int] = []
    strategy: str = "dist"    # dist=最短距离 / time=最短时间
    transport: str = "walk"   # walk=步行 / bike=自行车


class NavigateResponse(BaseModel):
    path_ids: List[int]
    path_names: List[str]
    path_coords: List[List[float]]
    total_cost: float
    cost_unit: str


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


class XHSPlanRequest(BaseModel):
    keyword: str
    days: int = 1
