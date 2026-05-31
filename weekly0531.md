# OSM 路网缓存优化更新说明

更新日期：2026-05-31

## 1. 更新目标

本次更新聚焦全国景点 OSM 导航的性能优化。

更新前，首次请求某个城市的导航路线时，后端需要调用 OSMnx 在线下载并构建整座城市的路网。进程内存缓存会在后端重启后丢失，因此重启服务后仍可能再次等待较长时间。

本次更新增加两层持久缓存：

1. 城市路网 GraphML 文件缓存：避免服务重启后重新联网下载路网。
2. 已计算路线 PostgreSQL 缓存：相同起点、终点和交通方式的路线可以直接返回。

仅修改了后端、数据库迁移、运行工具和后端测试，没有修改前端代码，也没有导入北京市全部景点。

## 2. 缓存流程

导航请求 `POST /navigate/osm` 到达后端后，按以下顺序处理：

```text
路线结果数据库缓存
  -> 命中：直接返回路线
  -> 未命中：继续获取城市路网

城市路网内存缓存
  -> 命中：直接计算路线
  -> 未命中：继续读取 GraphML

本地 GraphML 文件缓存
  -> 命中：从磁盘加载图，再计算路线
  -> 未命中：通过 OSMnx 联网下载，保存 GraphML，再计算路线
```

缓存按照 `城市 + 交通方式` 隔离。`walk` 和 `bike` 不会复用同一份路网，也不会自动互相降级。

路线缓存 key 格式：

```text
osm:v1:{city}:{transport}:{start_spot_id}:{end_spot_id}
```

路线缓存区分方向。例如“故宫博物院 -> 颐和园”和“颐和园 -> 故宫博物院”是两条独立缓存。

## 3. 主要改动

### 3.1 城市路网 GraphML 持久缓存

修改文件：`src/osm_service.py`

- 保留进程内 LRU 缓存。
- 新增 GraphML 文件读取和写入。
- 默认缓存目录：`data/osm_graphs/`。
- 默认 OSMnx HTTP 响应缓存目录：`data/osmnx_cache/`。
- GraphML 写入采用临时文件后原子替换，下载失败时不会覆盖已有可用缓存。
- 增加更清晰的路网加载、最近节点、路径距离和耗时日志。
- 保持返回坐标顺序为 `[latitude, longitude]`。

可选环境变量：

```text
OSM_GRAPH_CACHE_DIR
OSMNX_HTTP_CACHE_DIR
```

### 3.2 PostgreSQL 路网缓存元数据

新增迁移：`alembic/versions/0003_osm_graph_cache.py`

新增模型：`OSMGraphCache`

新增表：`osm_graph_cache`

该表只保存 GraphML 元数据，不保存完整节点和边：

| 字段 | 用途 |
| --- | --- |
| `city` | 城市 |
| `transport` | `walk` 或 `bike` |
| `place_query` | OSMnx 查询名称 |
| `graph_path` | GraphML 文件路径 |
| `node_count` | 节点数 |
| `edge_count` | 边数 |
| `file_size_bytes` | 文件大小 |
| `status` | 缓存状态 |
| `last_error` | 最近一次错误 |
| `downloaded_at` | 下载时间 |
| `updated_at` | 更新时间 |

### 3.3 已计算路线缓存

修改文件：`src/routers/navigation.py`

- `/navigate/osm` 计算前查询已有 `RouteCache`。
- 命中后直接返回已保存路线。
- 未命中时调用 OSMService 规划路线，成功后写入 `RouteCache`。
- 缓存损坏或过期时自动删除并重新计算。
- 缓存写入失败不会影响本次正常导航结果。

### 3.4 路网预加载工具

新增文件：`tools/preload_osm_graphs.py`

默认读取数据库中启用的全国景点城市，并预加载 `walk + bike`：

```powershell
uv run tools/preload_osm_graphs.py
```

仅预加载北京：

```powershell
uv run tools/preload_osm_graphs.py --city 北京
```

仅预加载北京步行路网：

```powershell
uv run tools/preload_osm_graphs.py --city 北京 --transport walk
```

强制重新下载北京步行路网，并清理对应路线结果缓存：

```powershell
uv run tools/preload_osm_graphs.py --city 北京 --transport walk --force
```

### 3.5 Git 忽略规则

修改文件：`.gitignore`

新增忽略目录：

```text
data/osm_graphs/
data/osmnx_cache/
cache/
```

大型运行期缓存文件不会提交到仓库。

## 4. 北京预加载实测结果

已于 2026-05-31 完成北京路网预加载：

| 交通方式 | 节点数 | 边数 | GraphML 大小 | 首次下载耗时 |
| --- | ---: | ---: | ---: | ---: |
| `walk` | 346875 | 966580 | 448.43 MB | 1077.92 秒 |
| `bike` | 296210 | 748767 | 359.52 MB | 1296.72 秒 |
| 合计 | 643085 | 1715347 | 807.95 MB | 约 39.6 分钟 |

GraphML 保存目录：

```text
D:\Code\Tourism_system\data\osm_graphs
```

该结果说明北京的步行和骑行路网均已成功保存。日常联调时不要删除此目录，否则需要重新联网下载。

## 5. 数据库升级

执行：

```powershell
uv run python -m alembic upgrade head
```

已验证 PostgreSQL 成功执行：

```text
0002_diary_poi_id -> 0003_osm_graph_cache
```

查看路网缓存元数据：

```powershell
docker compose exec db psql -U campus_user -d campus_nav -c "SELECT city, transport, node_count, edge_count, file_size_bytes, status, downloaded_at FROM osm_graph_cache ORDER BY city, transport;"
```

查看北京路线结果缓存：

```powershell
docker compose exec db psql -U campus_user -d campus_nav -c "SELECT cache_key, distance_m, duration_s, created_at FROM route_cache WHERE cache_key LIKE 'osm:v1:北京:%';"
```

## 6. 前端联调方法

### 6.1 启动数据库

```powershell
docker compose up -d db
```

### 6.2 启动后端

测试延迟时不要使用 `--reload`，避免开发模式热重载干扰计时：

```powershell
uv run uvicorn src.api:app
```

### 6.3 启动前端

Windows 环境中 Vite 默认绑定 IPv6 地址 `::1:3000` 时可能出现 `EACCES`。显式绑定 IPv4：

```powershell
cd frontend
npm run dev -- --host 127.0.0.1 --port 3000
```

浏览器访问：

```text
http://127.0.0.1:3000/?scope=national
```

如果本机端口 `3000` 仍不可用，可以改为：

```powershell
npm run dev -- --host 127.0.0.1 --port 5173
```

### 6.4 界面操作

1. 点击左侧“导航”。
2. 点击“校外 OSM”。
3. 起点选择“故宫博物院（北京）”。
4. 终点选择“颐和园（北京）”。
5. 选择“步行”或“骑行”。
6. 点击“开始校外导航”。
7. 确认地图出现路线，侧栏显示距离、耗时、路段数和节点数。

## 7. 延迟测试方法

在浏览器按 `F12`，进入 `Network`，查看：

```text
POST /navigate/osm
```

建议分别记录以下三种情况：

| 场景 | 准备操作 | 预期结果 |
| --- | --- | --- |
| GraphML 磁盘冷加载 | 清理路线缓存并重启后端 | 需要读取约 448 MB 或 360 MB 文件，耗时相对较长 |
| 内存路网命中 | 不重启后端，清理路线缓存后再次规划 | 无需读取 GraphML，速度明显提升 |
| PostgreSQL 路线缓存命中 | 不清理缓存，重复完全相同请求 | 最快，直接读取 `RouteCache` |

只清理北京已计算路线，不删除 GraphML：

```powershell
docker compose exec db psql -U campus_user -d campus_nav -c "DELETE FROM route_cache WHERE cache_key LIKE 'osm:v1:北京:%';"
```

## 8. 测试覆盖

本次更新补充了以下自动化测试：

- GraphML 文件命中时不发起联网下载。
- 文件不存在时下载并保存 GraphML。
- 强制刷新失败时保留旧 GraphML。
- `walk` 和 `bike` 使用独立缓存。
- 路线输出坐标顺序固定为 `[latitude, longitude]`。
- 首次 `/navigate/osm` 请求写入路线缓存。
- 相同请求第二次命中路线缓存。
- 反向路线和不同交通方式不会错误复用缓存。
- 预加载工具只处理启用城市。
- `--force` 仅清理目标城市和交通方式的路线结果缓存。
- `OSMGraphCache` 元数据可以正常新增和更新。

本地测试结果：

```text
44 passed
```

## 9. 本次涉及文件

新增文件：

```text
alembic/versions/0003_osm_graph_cache.py
tools/preload_osm_graphs.py
tests/test_osm_graph_cache_metadata.py
tests/test_osm_preload.py
```

修改文件：

```text
.gitignore
src/create_tables.py
src/models.py
src/osm_service.py
src/routers/navigation.py
tests/test_osm_api.py
tests/test_osm_service.py
tests/test_script_entrypoints.py
```

## 10. 后续建议

1. 先完成“故宫博物院 -> 颐和园”步行和骑行的三档延迟记录。
2. 根据现有全国景点涉及城市，按需逐个预加载，不要一次性盲目下载全部城市。
3. 全国 OSM 导航稳定后，再通过独立 seed 文件或导入脚本小规模补充北京景点。
