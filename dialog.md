################################
# 2026/4/6
 - 扩展全国景点模型：NationalSpot 增加赏花/XHS 元数据；新增 NationalSpotXHSNote，支持一个景点挂多条小红书预览。
 - 扩展接口契约：/map/national-spots 现在返回 
xhs_note_count、xhs_notes_preview、xhs_fetch_status、xhs_fetch_message、xhs_cookie_needs_refresh、xhs_last_fetched_at，/spots/search 也补了 XHS 摘要字段。
 - 统一小红书抓取链路：新增 src\national_spot_xhs.py、src\national_spot_importer.py，复用现有 Spider_XHS/skill；Cookie 失效时会明确返回“更新 .env 中 
XHS_COOKIE”。
 - 补齐导入工具和数据：新增 
tools\import_national_flower_spots.py、tools\crawl_flower_spots.py、data\national_flower_spots.json，tools\init_national_spots.py 也已接入共享 importer。
 - 补齐后端回归：地图接口、搜索、OSM 合同、导入与 Cookie 失效场景都已覆盖。

下一步只需要配好有效的 XHS_COOKIE，然后执行： uv run python tools/import_national_flower_spots.py

按城市增量抓取可用： uv run python tools/crawl_flower_spots.py --city 武汉
