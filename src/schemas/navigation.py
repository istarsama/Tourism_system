"""导航相关请求/响应 Pydantic 模型。"""

from typing import List, Optional

from pydantic import BaseModel, Field


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
    start_spot_id: int = Field(..., description="起点 NationalSpot.id")
    end_spot_id: int = Field(..., description="终点 NationalSpot.id")
    transport: str = Field("walk", description="出行方式，仅支持 walk 或 bike")


class OSMNavigateResponse(BaseModel):
    city: str = Field(..., description="导航所在城市")
    transport: str = Field(..., description="出行方式，walk 或 bike")
    start_spot_id: int = Field(..., description="起点 NationalSpot.id")
    end_spot_id: int = Field(..., description="终点 NationalSpot.id")
    node_ids: List[int] = Field(..., description="OSM 路网节点 ID 序列")
    path_coords: List[List[float]] = Field(
        ...,
        description="OSM 路径坐标点，顺序固定为 [lat, lng]，可直接用于前端 OSM/Leaflet 折线",
    )
    total_distance_m: float = Field(..., description="路线总距离，单位米")
    segment_count: int = Field(..., description="路段数量")
    segment_distances_m: List[float] = Field(..., description="相邻 OSM 节点之间的路段距离，单位米")
    estimated_duration_s: float = Field(..., description="按出行方式估算的耗时，单位秒")


class XHSPlanRequest(BaseModel):
    keyword: str
    days: int = 1
