# 🎓 校园旅游与日记分享系统

**基于 DeepSeek 大模型的个性化旅游导览与社交平台**

---

## 🚀 快速开始

### 1️⃣ 启动测试平台（推荐）

```bash
python run_tests.py
```

### 2️⃣ 启动后端服务

```bash
uv run uvicorn src.api:app --reload
```

访问: http://localhost:8000

### 3️⃣ 前端页面

打开 `frontend/index.html`

---

## 📁 项目结构

```
Tourism_system/
├── 📄 run_tests.py        # 统一测试与工具平台
├── 📂 src/                # 核心源代码
├── 📂 tools/              # 功能工具（数据库、爬虫）
├── 📂 tests/              # 测试代码
├── 📂 docs/               # 文档
├── 📂 data/               # 数据文件
└── 📂 frontend/           # 前端文件
```

---

## 🛠️ 功能菜单

通过 `python run_tests.py` 可访问所有功能：

### 📋 业务测试
- **1** - 注册测试
- **2** - 登录测试  
- **3** - 导航测试
- **4** - 搜索测试
- **5** - 评论流程
- **6** - 业务流测试
- **7** - AI 闲聊
- **8** - AI RAG

### 🔧 数据库工具
- **d** - 查看数据库
- **s** - 查看景点
- **t** - 查看表结构
- **u** - 升级数据库

### 🕷️ 爬虫工具
- **c** - 爬取数据
- **w** - 测试爬虫
- **l** - 测试长度

### 🚀 批量操作
- **a** - 运行全部测试

---

## 📚 详细文档

查看 `docs/` 目录：

- [README.md](docs/README.md) - 完整项目文档
- [CRAWL_IMPORT_GUIDE.md](docs/CRAWL_IMPORT_GUIDE.md) - 爬虫使用指南
- [PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md) - 项目结构说明
- [QUICK_FIX.md](docs/QUICK_FIX.md) - 常见问题解决

---

## ⚙️ 环境配置

`.env` 文件配置：

```env
DATABASE_URL=mysql+pymysql://root:root@127.0.0.1:3306/campus_nav
SECRET_KEY=your-secret-key
DEEPSEEK_API_KEY=your-deepseek-api-key
TAVILY_API_KEY=your-tavily-api-key
XHS_COOKIE=your-xiaohongshu-cookie
```

---

## 🎯 核心功能

- ✅ 智能导航路径规划
- ✅ AI 对话助手 (DeepSeek V3)
- ✅ RAG 知识库检索
- ✅ 日记分享与评论
- ✅ 小红书数据爬取
- ✅ 多维推荐算法

---

## 📊 技术栈

- **后端**: FastAPI + SQLModel + MySQL
- **AI**: DeepSeek V3 + Tavily Search
- **爬虫**: 小红书 Spider
- **算法**: Dijkstra + 模糊搜索

---

需要帮助？运行 `python run_tests.py` 查看所有功能！
