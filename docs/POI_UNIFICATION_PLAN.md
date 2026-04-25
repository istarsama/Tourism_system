# POI 统一地点体系设计

## 当前目标

后端逐步从旧的双字段地点关联：

- `Diary.spot_id`：校园地图节点
- `Diary.national_spot_id`：全国景点

迁移到统一字段：

- `Diary.poi_id`：统一地点主键，关联 `poi.id`

旧字段暂时保留，保证现有前端接口和历史数据不受影响。

## 数据模型

`POI` 是统一地点主表：

- `source="campus"` + `source_ref=<campus spot id>` 表示校园点位
- `source="national_spot"` + `source_ref=<national_spot id>` 表示全国景点

`POIGeometry` 存坐标：

- 校园点位使用 `geometry_type="campus_pixel"`，写入 `x_pixel/y_pixel`
- 全国景点使用 `geometry_type="wgs84_point"`，写入 `latitude/longitude`

`POIAlias` 存别名，后续搜索、清洗、小红书景点匹配都应优先查这里。

## 兼容阶段写入规则

创建日记时仍接受现有前端字段：

- `scope="campus"` 时读取 `spot_id`
- `scope="national"` 时读取 `national_spot_id`

后端根据旧字段解析对应 `POI`，并同步写入 `Diary.poi_id`。如果映射暂时不存在，旧字段仍然保存，启动时的回填任务会在 POI 同步后补齐。

## 启动同步

FastAPI lifespan 中会执行：

1. `sync_national_spots_to_poi()`：把全国景点同步到 POI。
2. `sync_campus_graph_to_poi()`：把校园地图景点同步到 POI。
3. `backfill_diary_poi_ids()`：为历史日记补齐 `poi_id`。

这三个函数都是幂等的，可以重复运行。

## Alembic 迁移

本轮新增：

- `0001_baseline_current_models.py`：按当前 SQLModel 元数据建立基线表结构。
- `0002_diary_poi_id.py`：为 `diary` 增加 `poi_id`、索引和 PostgreSQL 外键。

本地执行：

```bash
uv run alembic upgrade head
```

如果数据库已经由旧版 `init_db()` 创建过，`0001` 会保持幂等，`0002` 只补缺失字段。

## 后续收口步骤

1. 路由查询优先按 `poi_id` 过滤，旧字段只作为兼容 fallback。
2. 前端创建日记时改传 `poi_id`，后端继续兼容旧字段一段时间。
3. 小红书爬虫导入、OSM 导航、搜索推荐统一使用 `poi_id`。
4. 确认无旧客户端后，评估移除 `Diary.spot_id` / `Diary.national_spot_id`。
