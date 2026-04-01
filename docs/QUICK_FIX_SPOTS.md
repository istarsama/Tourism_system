# 🚀 快速修复指南

## 问题
景点显示不出来？看这里！

## 原因
`national_spot` 表是空的。JSON 数据存在但没被导入到数据库。

## 解决 (一行命令)
```bash
python tools/init_national_spots.py
```

## 完整启动步骤

### 1️⃣ 初始化数据（第一次需要）
```bash
python tools/init_national_spots.py
```

### 2️⃣ 启动后端（终端1）
```bash
uv run uvicorn src.api:app --reload
```
✅ 看到 "Uvicorn running on http://127.0.0.1:8000"

### 3️⃣ 启动前端（终端2）
```bash
cd frontend
npm run dev
```
✅ 看到 "VITE ready in XXX ms"

### 4️⃣ 打开浏览器
访问：http://localhost:3000/#/nav?scope=national

---

## ✨ 现在应该能看到：
- 故宫博物院 (北京)
- 秦始皇兵马俑博物馆 (西安)
- 外滩 (上海)
- ... 等等 10 个景点

---

## 😕 仍然看不到？

### 检查步骤
```bash
# 检查数据是否导入成功
python -c "
import sys; sys.path.insert(0, 'src')
from database import engine
from models import NationalSpot
from sqlmodel import Session, select
session = Session(engine)
count = len(session.exec(select(NationalSpot)).all())
print(f'数据库中有 {count} 条数据 (应该是10)')
"
```

### 常见问题
| 症状 | 解决方案 |
|------|--------|
| 依然看不到景点 | 重启前端 (Ctrl+C 再运行 npm run dev) |
| 看到 404 错误 | 确认后端运行在 8000 端口 |
| 看到 CORS 错误 | 刷新页面 (Ctrl+Shift+R) |

---

详细说明见：[NATIONAL_SPOTS_FIX.md](./NATIONAL_SPOTS_FIX.md)
