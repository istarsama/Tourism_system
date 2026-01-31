# Vue 3 校园导游系统

基于 Vue 3 + Vite + Pinia 重构的前端项目。

## 功能特性

- ✅ 用户认证（登录/注册）
- ✅ 交互式地图（缩放、平移、节点选择）
- ✅ 智能导航（最短路径、最少时间）
- ✅ 景点搜索（模糊匹配）
- ✅ 社区日记（浏览、创建、评论）
- ✅ AI 智能助手（RAG 对话）
- ✅ 路径动画展示

## 技术栈

- **框架**: Vue 3 (Composition API)
- **状态管理**: Pinia
- **构建工具**: Vite
- **HTTP 客户端**: Axios
- **样式**: 原生 CSS + CSS Variables

## 项目结构

```
frontend-vue/
├── src/
│   ├── api/              # API 接口封装
│   │   └── index.js
│   ├── stores/           # Pinia 状态管理
│   │   ├── auth.js
│   │   ├── map.js
│   │   └── diary.js
│   ├── components/       # Vue 组件
│   │   ├── MapCanvas.vue       # 地图画布
│   │   ├── Sidebar.vue         # 侧边栏
│   │   ├── UserPanel.vue       # 用户面板
│   │   ├── NavigationPanel.vue # 导航控制
│   │   ├── DiaryPanel.vue      # 日记列表
│   │   ├── SearchInput.vue     # 搜索框
│   │   ├── AuthModal.vue       # 登录注册弹窗
│   │   ├── DiaryDetailModal.vue# 日记详情
│   │   └── ChatPanel.vue       # AI 聊天
│   ├── App.vue           # 根组件
│   ├── main.js           # 入口文件
│   └── style.css         # 全局样式
├── index.html
├── package.json
└── vite.config.js
```

## 安装与运行

```bash
# 安装依赖
npm install

# 开发模式
npm run dev

# 构建生产版本
npm run build

# 预览生产版本
npm run preview
```

## 环境变量

创建 `.env` 文件配置后端 API 地址：

```
VITE_API_BASE=http://127.0.0.1:8000
```

## 对比原版改进

| 方面 | 原版 (JS) | Vue 版本 |
|------|-----------|----------|
| 代码组织 | 单文件 1200+ 行 | 组件化，模块化 |
| 状态管理 | 全局变量 | Pinia (响应式) |
| 代码复用 | 重复逻辑多 | 组合式函数 |
| 类型安全 | 无 | Props 验证 |
| 开发体验 | 手动 DOM 操作 | 声明式渲染 |
| 性能 | 手动优化 | Vue 自动优化 |
| 可维护性 | 中等 | 高 |

## 与后端对接

确保后端 API 已启动 (默认 `http://127.0.0.1:8000`)，前端通过 Vite 代理自动转发请求。

## 注意事项

- 地图图片路径需放在 `public/frontend/map.png`
- Logo 图片路径需放在 `public/data/xiaohui.jpg`
- 确保后端已配置 CORS 允许跨域请求
