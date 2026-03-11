# 🎯 国家级景点显示问题解决方案

## 问题诊断

**症状**：运行项目后，国家级景点（National Spots）界面无法显示景点信息

**根本原因**：`NationalSpot` 数据库表为空，虽然 JSON 数据文件 (`data/national_spots.json`) 存在 10 条景点数据，但这些数据还没有被导入到数据库中。

### 工作流程说明

```
data/national_spots.json (JSON文件)
         ↓
   需要运行导入脚本
         ↓
tools/init_national_spots.py (导入脚本)
         ↓
MySQL: national_spot 表 (数据库表)
         ↓
后端 API: /map/national-spots (FastAPI接口)
         ↓
前端: features/map/national (Vue组件)
```

---

## ✅ 解决方案

### 方法 1️⃣：快速修复（推荐）

只需运行一条命令：

```bash
python tools/init_national_spots.py
```

**输出预期**：
```
✅ 导入完成：新增 10 条，更新 0 条，跳过 0 条。
```

### 方法 2️⃣：通过测试菜单

```bash
python run_tests.py
```

然后在菜单中选择合适的选项（如数据库恢复工具等）。

---

## 🔍 验证修复

### 1. 检查数据库中的数据

```bash
python -c "
import sys
sys.path.insert(0, 'src')
from database import engine
from models import NationalSpot
from sqlmodel import Session, select

session = Session(engine)
spots = session.exec(select(NationalSpot)).all()
print(f'✅ 数据库中有 {len(spots)} 条景点数据')
for spot in spots:
    print(f'  - {spot.name} ({spot.city})')
"
```

### 2. 启动后端并测试 API

```bash
# 终端1：启动后端
uv run uvicorn src.api:app --reload

# 终端2：测试API（等待3秒让服务启动）
curl http://localhost:8000/map/national-spots | python -m json.tool
```

### 3. 启动前端查看效果

```bash
cd frontend
npm run dev
```

访问 `http://localhost:3000/#/nav?scope=national`，应该能看到景点列表。

---

## 📋 已导入的景点列表

当前共有 **10** 条景点数据：

| 景点名称 | 城市 | 类型 | 评分 |
|---------|------|------|------|
| 故宫博物院 | 北京 | 人文景观 | 4.9 ⭐ |
| 颐和园 | 北京 | 历史遗迹 | 4.8 ⭐ |
| 秦始皇兵马俑博物馆 | 西安 | 历史遗迹 | 4.9 ⭐ |
| 华清宫 | 西安 | 历史遗迹 | 4.6 ⭐ |
| 外滩 | 上海 | 人文景观 | 4.7 ⭐ |
| 上海迪士尼乐园 | 上海 | 主题乐园 | 4.8 ⭐ |
| 西湖风景名胜区 | 杭州 | 自然景观 | 4.9 ⭐ |
| 黄山风景区 | 黄山 | 自然景观 | 4.8 ⭐ |
| 九寨沟风景区 | 阿坝 | 自然景观 | 4.9 ⭐ |
| 鼓浪屿 | 厦门 | 人文景观 | 4.7 ⭐ |

---

## 🔧 相关文件

| 文件 | 说明 |
|------|------|
| `data/national_spots.json` | 景点数据源文件 |
| `tools/init_national_spots.py` | 数据导入脚本 |
| `src/models.py` | 数据库模型定义 |
| `src/api.py` | API 接口 (行 341) |
| `frontend/src/stores/nationalMap.js` | 前端状态管理 |

---

## 💡 扩展：添加更多景点

如果需要添加更多景点，编辑 `data/national_spots.json` 文件，然后重新运行导入脚本：

```json
{
  "name": "景点名称",
  "type": "景点类型（如：人文景观、自然景观等）",
  "latitude": 39.9163,
  "longitude": 116.397,
  "city": "城市名称",
  "description": "景点描述",
  "rating": 4.9,
  "is_active": true
}
```

然后运行：
```bash
python tools/init_national_spots.py
```

---

## 📞 故障排除

### 问题：导入脚本失败

**检查项**：
```bash
# 1. 检查JSON文件格式
python -c "import json; json.load(open('data/national_spots.json', encoding='utf-8')); print('✅ JSON格式正确')"

# 2. 检查数据库连接
python -c "
import sys
sys.path.insert(0, 'src')
from database import engine
from sqlalchemy import inspect
inspector = inspect(engine)
print(f'✅ 数据库连接正常，表: {inspector.get_table_names()}')
"
```

### 问题：前端仍然看不到景点

1. ✅ 确认后端已启动 (`uv run uvicorn src.api:app --reload`)
2. ✅ 打开浏览器开发者工具 (F12) → Network 标签
3. ✅ 检查 `/map/national-spots` 请求是否返回 200 状态码
4. ✅ 检查响应数据是否包含景点信息

---

## 🎓 学习资源

- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [SQLModel 文档](https://sqlmodel.tiangolo.com/)
- [Vue.js 文档](https://vuejs.org/)
- [Pinia 状态管理](https://pinia.vuejs.org/)

---

**最后更新**：2026-03-11  
**问题修复日期**：2026-03-11
