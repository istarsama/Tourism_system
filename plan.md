# 旅游系统后端优化计划

## 目标
从北邮校内特化地图系统扩展为双地图模式的综合旅游平台，并通过小红书爬虫+协同过滤实现智能路线推荐。

## 实施策略
1. **优先级**：先完成OSM地图扩展（阶段一），再实施路线推荐（阶段二）
2. **地图模式**：双地图模式（校内canvas + 全国景点OSM）
3. **推荐算法**：混合数据源 + 协同过滤
4. **地理范围**：特定景点集（国内热门5A/4A景区）

---

## 阶段一：OSM地图扩展（7-10天）

### Phase 1: 基础设施准备（2天）

**步骤 1.1** - OSM技术栈选型与数据准备
- 选择Python库：`osmnx`（路网构建+路径规划）+ `networkx`（图算法）+ `geopy`（地理编码）
- 安装依赖：`pip install osmnx networkx folium geopy`
- 定义景点数据集范围：收集国内Top 100热门景点POI数据（经纬度、名称、类型）
- 预下载城市路网：使用osmnx下载Top 10热门城市的路网图缓存到本地（北京、上海、西安等）
- 设计景点分类体系：自然景观/人文景观/主题乐园/历史遗迹等

**步骤 1.2** - 数据库扩展
- 在 [models.py](src/models.py) 新增模型：
  - `NationalSpot` 表（全国景点）：id, name, type, latitude, longitude, description, city, rating
  - `MapConfig` 表（地图配置）：scope（校内/全国）、center_lat、center_lng、zoom_level
- 在 [create_tables.py](src/create_tables.py) 添加建表逻辑
- 编写数据库迁移脚本（在 `tests/tools/` 下创建 `migrate_to_dual_map.py`）

**步骤 1.3** - 景点数据初始化
- 创建 [tools/init_national_spots.py](tools/init_national_spots.py)：
  - 从CSV/JSON导入Top 100景点数据
  - 使用 `geopy.geocoders.Nominatim` 验证/补全经纬度
  - 批量插入 `NationalSpot` 表
- 创建种子数据文件 [data/national_spots.json](data/national_spots.json)

### Phase 2: 后端API开发（3天）

**步骤 2.1** - 地图模式切换API（*parallel with 2.2*）
- 在 [api.py](src/api.py) 新增端点：
  - `GET /map/mode?scope=campus|national` - 返回地图配置（中心点、缩放级别、数据源类型）
  - `GET /map/campus-graph` - 返回原有校内地图JSON（重构自 `/graph`）
  - `GET /map/national-spots?city=北京&type=自然景观` - 返回全国景点列表（支持过滤）

**步骤 2.2** - OSM导航功能实现（*parallel with 2.1*）
- 创建 [src/osm_service.py](src/osm_service.py) 新增 `OSMService` 类：
  - `get_city_graph(city_name)` - 下载并缓存城市路网图（使用 `@lru_cache`）
  - `route_planning(city, start_lat, start_lng, end_lat, end_lng)` - 本地计算最短路径
  - 使用 `ox.distance.nearest_nodes()` 定位最近节点，`nx.shortest_path()` 计算路径
  - 返回：路径坐标列表、总距离、节点序列
- 在 [api.py](src/api.py) 新增：
  - `POST /navigate/osm` - 请求体：`{start_spot_id, end_spot_id, transport}`
  - 查询 `NationalSpot` 获取经纬度和所属城市，调用 `OSMService.route_planning()`，返回路线详情

**步骤 2.3** - 搜索功能扩展
- 修改 [api.py](src/api.py) 的 `/spots/search`：
  - 增加 `scope` 参数（campus/national）
  - 根据scope查询不同数据源（CampusGraph vs NationalSpot）
  - 保持thefuzz模糊匹配逻辑

**步骤 2.4** - 日记系统适配（*depends on 2.1*）
- 修改 [models.py](src/models.py) 的 `Diary` 表：
  - 添加字段：`scope` (enum: 'campus'/'national'), `national_spot_id` (可选)
  - `spot_id` 保留用于校内，新增 `national_spot_id` 用于全国景点
- 修改 [api.py](src/api.py) 的日记API：
  - `POST /diaries/` 接受 `scope` 和对应的景点ID
  - `GET /diaries/spot/{id}?scope=campus` 根据scope查询

### Phase 3: 前端集成（2-3天）

**步骤 3.1** - 地图组件架构
- 在 [frontend/app.js](frontend/app.js) 新增模块：
  - `MapManager` 类：管理双地图切换逻辑
  - `CampusMapRenderer` - 封装现有Canvas渲染
  - `OSMMapRenderer` - 使用Leaflet.js集成OSM
- 添加Leaflet依赖到 [frontend/index.html](frontend/index.html)

**步骤 3.2** - UI交互设计
- 在页面顶部添加地图切换器（Toggle: "校园导览" ↔ "全国景点"）
- 根据模式动态渲染不同组件：
  - 校园模式：显示现有Canvas地图 + 下拉框
  - 全国模式：显示Leaflet OSM地图 + 搜索框 + 标记
- 保持现有功能在校园模式下不受影响

**步骤 3.3** - OSM地图渲染
- 初始化Leaflet地图（中心坐标从 `/map/mode?scope=national` 获取）
- 调用 `/map/national-spots` 获取景点，在地图上添加Marker
- 实现点击Marker弹出信息窗口（景点名称、类型、评分、"查看日记"按钮）
- 点击两个景点自动调用 `/navigate/osm` 绘制路线

### Phase 4: 测试与验证（1-2天）

**验证步骤**：
1. 单元测试：在 [tests/test_nav.py](tests/test_nav.py) 添加 `test_osm_navigation()` 测试OSRM API调用
2. 集成测试：验证双地图切换后数据正确加载
3. 性能测试：100个景点标记的渲染性能，OSM API响应时间
4. 跨浏览器测试：Chrome/Firefox/Safari 下Leaflet显示正常
5. 手动测试场景：
   - 切换到全国模式 → 搜索"故宫" → 添加标记 → 规划到"颐和园"的路线
   - 点击全国景点Marker → 查看/发布日记 → 验证数据关联正确

---

## 阶段二：小红书路线推荐（5-7天）

### Phase 1: 爬虫增强与数据收集（2天）

**步骤 1.1** - 路线游记专项爬取（*parallel with 1.2*）
- 扩展 [crawler.py](src/crawler.py) 的 `XHSCrawler` 类：
  - `crawl_route_notes(keywords=['北京三日游', '西安路线'])` - 针对路线关键词爬取
  - 提取笔记中的景点序列（使用NER/正则提取地名）
- 在 [models.py](src/models.py) 新增：
  - `RecommendedRoute` 表：id, title, spot_ids (JSON数组), source ('xhs'/user'), popularity_score, created_at
  - `RouteSpot` 关联表：route_id, spot_id, visit_order

**步骤 1.2** - 定时任务系统（*parallel with 1.1*）
- 创建 [src/scheduler.py](src/scheduler.py)：
  - 使用 `APScheduler`
  - 定义任务：`daily_crawl_routes()` - 每日爬取Top 10城市的热门路线
  - 混合模式：定时爬取 + 用户请求时补充爬取
- 修改 [main.py](src/main.py) 集成定时任务

**步骤 1.3** - 景点提取与匹配
- 创建 [src/nlp_utils.py](src/nlp_utils.py)：
  - `extract_spots_from_text(content)` - 使用jieba分词 + 地名词库识别景点
  - `match_to_db(spot_names)` - 将提取的名称匹配到 `CampusGraph` 或 `NationalSpot`
- 在 [tools/import_crawled_data.py](tools/import_crawled_data.py) 中调用，处理爬取结果

### Phase 2: 协同过滤推荐引擎（2天）

**步骤 2.1** - 用户行为数据收集（*depends on 阶段一完成*）
- 修改 [models.py](src/models.py) 新增：
  - `UserVisit` 表：user_id, spot_id (校内/全国mixed), timestamp, duration
  - `UserRating` 表：合并现有Comment.score逻辑
- 在 [api.py](src/api.py) 添加埋点：
  - 查看景点详情时记录 `UserVisit`
  - 评论时同步更新 `UserRating`

**步骤 2.2** - 协同过滤算法实现
- 创建 [src/recommender.py](src/recommender.py)：
  - `class CollaborativeFilter` - 基于用户-景点评分矩阵
  - `compute_similarity()` - 计算用户/物品相似度（余弦相似度）
  - `recommend_spots(user_id, n=10)` - 返回推荐景点列表
  - `recommend_route(user_id, start_spot_id)` - 结合推荐景点 + Dijkstra生成路线

**步骤 2.3** - 路线生成策略
- 在 [algorithms.py](src/algorithms.py) 新增：
  - `generate_personalized_route(user_id, start_id, days, preferences)`：
    1. 从 `CollaborativeFilter` 获取推荐景点列表
    2. 过滤用户已访问景点
    3. 根据天数和距离约束，贪心选择景点
    4. 调用 `plan_multi_point_route()` 生成完整路线
  - 返回：`{route_name, spot_ids, path_coords, estimated_time}`

### Phase 3: 推荐API开发（1天）

**步骤 3.1** - 路线推荐端点
- 在 [api.py](src/api.py) 新增路由：
  - `GET /routes/recommended?user_id=1&limit=5` - 获取热门/推荐路线列表
  - `POST /routes/generate` - 生成个性化路线：
    ```json
    {
      "user_id": 1,
      "start_spot_id": 10,
      "preferences": {"type": "自然景观", "days": 3},
      "algorithm": "collaborative" | "popularity" | "ai"
    }
    ```
  - `GET /routes/{route_id}` - 获取路线详情（景点列表、路径、游记）

**步骤 3.2** - AI路线生成（可选增强）
- 在 [ai.py](src/ai.py) 新增：
  - `generate_route_by_ai(user_query, user_context)` - 用DeepSeek根据用户描述生成路线
  - 整合RAG：检索类似路线的游记，辅助LLM生成

### Phase 4: 前端展示与测试（2天）

**步骤 4.1** - 路线推荐页面
- 在 [frontend/index.html](frontend/index.html) 新增"路线推荐"Tab
- 在 [frontend/app.js](frontend/app.js) 实现：
  - 展示推荐路线列表（卡片模式：标题、景点预览、热度、"查看详情"按钮）
  - 点击路线 → 在地图上高亮显示路径 + 景点标记
  - "生成我的路线"按钮 → 弹出配置对话框 → 调用 `/routes/generate` → 展示结果

**步骤 4.2** - 验证测试
1. 爬虫功能：运行 [src/tools/Spider_XHS/test_spider.py](src/tools/Spider_XHS/test_spider.py) 验证路线爬取
2. 推荐算法：在 [tests/](tests/) 创建 `test_recommender.py`：
   - 模拟用户评分数据
   - 验证协同过滤输出Top N推荐
   - 验证路线生成的景点顺序合理性
3. API测试：使用Postman/curl测试所有新端点
4. 性能测试：100个用户 × 1000个景点的推荐计算耗时
5. 端到端测试：用户登录 → 浏览景点 → 查看推荐路线 → 生成个性化路线 → 查看详情

---

## 相关文件清单

### 新增文件
- `src/osm_service.py` - OSM路网管理和路径规划服务
- `src/scheduler.py` - 定时爬虫任务
- `src/recommender.py` - 协同过滤推荐引擎
- `src/nlp_utils.py` - 景点提取NLP工具
- `tools/init_national_spots.py` - 景点数据初始化
- `tools/migrate_to_dual_map.py` - 数据库迁移脚本
- `data/national_spots.json` - 全国景点种子数据
- `tests/test_recommender.py` - 推荐系统测试

### 修改文件
- [src/models.py](src/models.py) - 添加 `NationalSpot`, `MapConfig`, `RecommendedRoute`, `UserVisit`, `UserRating`
- [src/api.py](src/api.py) - 新增地图、OSM导航、路线推荐相关端点
- [src/algorithms.py](src/algorithms.py) - 新增OSM路由、个性化路线生成
- [src/crawler.py](src/crawler.py) - 扩展路线爬取功能
- [src/main.py](src/main.py) - 集成定时任务
- [frontend/index.html](frontend/index.html) - 添加地图切换器、路线推荐Tab
- [frontend/app.js](frontend/app.js) - 实现双地图Manager、路线展示逻辑

---

## 技术决策记录

### 为什么选择双地图模式？
- **保留校内精细化体验**：Canvas地图支持像素级定制，适合校园导览
- **OSM扩展全国能力**：Leaflet + OSM提供完整的地理信息服务，无需重复造轮子
- **渐进式迁移**：分阶段开发，降低风险

### 为什么选择osmnx本地计算而非OSRM/百度/高德API？
- **纯Python实现**：无需外部服务依赖，降低系统复杂度
- **无API限制**：不受调用次数和并发限制
- **响应速度**：首次加载城市后本地计算，延迟更低
- **成本优势**：百度/高德API收费，OSRM需自建服务器
- **特定景点集友好**：只需预下载Top 10城市路网（~300MB），符合你的"特定景点集"策略
- **可控性强**：路由算法可自定义（最短距离/时间/避开拥堵）
- **备选方案**：如需实时路况，可接入高德Web服务API作为增强

### 为什么协同过滤而非深度学习？
- **数据量级**：当前用户/景点规模适合传统CF算法
- **可解释性**：推荐结果可追溯到相似用户
- **实施成本**：无需GPU资源，可在现有服务器运行
- **后续扩展**：数据积累后可升级为矩阵分解（SVD）或深度模型

### 混合数据源策略
- **定时爬取（离线）**：每日凌晨2点爬取Top 10城市热门路线 → 入库
- **实时爬取（在线）**：用户查询冷门目的地时触发 → 缓存24小时
- **优势**：平衡数据新鲜度和爬虫稳定性，避免Cookie失效风险

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| **小红书Cookie频繁失效** | 高 | 1. 实现Cookie池轮换 2. 降级到离线数据 3. 引入备用数据源（马蜂窝API） |
| **osmnx首次加载城市慢** | 中 | 1. 预下载并缓存Top 10城市路网 2. 显示加载进度条 3. 后台异步初始化 |
| **景点名称匹配错误** | 中 | 1. 建立景点别名词典 2. 人工审核高频错误 |
| **协同过滤冷启动** | 低 | 1. 对新用户使用热度推荐 2. 引导用户初始化偏好 |
| **前端Leaflet性能** | 低 | 1. 聚合标记（Marker Clustering） 2. 懒加载景点数据 |
| **路网数据占用内存** | 低 | 1. 限定为Top 10城市 2. 使用LRU缓存自动清理 3. 考虑持久化到磁盘 |

---

## 后续考虑

1. **移动端适配**：Leaflet地图在移动浏览器的响应式优化
2. **离线地图**：使用Service Worker缓存OSM瓦片，支持离线导览
3. **AR导航**：在校园模式下集成WebAR，叠加路线箭头
4. **多语言支持**：景点描述的中英文切换（OSM本身支持多语言）
5. **游戏化**：景点打卡积分、成就徽章系统