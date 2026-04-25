"""地图相关请求/响应 Pydantic 模型。"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


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
