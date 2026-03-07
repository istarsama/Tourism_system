# 🎉 Vue Router 重构完成指南

## ✅ 已完成的工作

### 1. 安装依赖
- ✅ 已安装 `vue-router@4`

### 2. 创建的新文件
- ✅ `src/router/index.js` - 路由配置文件
- ✅ `src/composables/useRouteQuery.js` - URL 参数读取工具

### 3. 修改的文件
- ✅ `src/main.js` - 注册路由插件
- ✅ `src/App.vue` - 添加全局模态框和路由监听
- ✅ `src/components/Sidebar.vue` - 使用路由导航代替状态切换
- ✅ `src/components/DiaryPanel.vue` - 点击日记跳转路由
- ✅ `src/components/DiaryDetailModal.vue` - 保持模态框形式
- ✅ `src/components/AuthModal.vue` - 保持模态框形式
- ✅ `src/components/UserPanel.vue` - 登录按钮触发路由参数

---

## 📖 路由使用说明

### 可用路由路径

| 路径 | 显示内容 | 说明 |
|------|---------|------|
| `/` | - | 自动重定向到 `/nav` |
| `/nav` | 导航面板 | 侧边栏显示导航功能 |
| `/diary` | 日记列表 | 侧边栏显示日记列表 |
| `/diary/:id` | 日记列表 + **模态框** | **侧边栏显示列表，同时弹出日记详情模态框** ⭐ |
| `/diary?spotId=123` | 筛选的日记列表 | 只显示指定景点的日记 |
| `?login=true` | 当前页面 + **模态框** | **保持当前页面，弹出登录模态框** ⭐ |

### 浏览器地址栏示例
```
http://localhost:5173/#/nav
http://localhost:5173/#/diary
http://localhost:5173/#/diary/25              ← 日记详情以模态框形式覆盖页面
http://localhost:5173/#/diary?spotId=5        ← 筛选景点 5 的日记
http://localhost:5173/#/nav?login=true        ← 在导航页面打开登录模态框
```

---

## 🎨 架构设计（保留原有 UI 交互）

### ⭐ 核心特性

**1. 模态框仍然是模态框**
- ✅ 日记详情：全屏模态框覆盖
- ✅ 登录表单：全屏模态框覆盖
- ❌ **不会**放到侧边栏里

**2. URL 仍然会变化**
- ✅ 每篇日记有独立 URL
- ✅ 可以分享链接
- ✅ 刷新页面保持状态
- ✅ 浏览器前进/后退可用

**3. 实现原理**
```
用户点击日记卡片
  ↓
router.push('/diary/25')
  ↓
App.vue 监听到路由变化
  ↓
显示 DiaryDetailModal（模态框覆盖整个页面）
  ↓
背景仍然是日记列表页面
```

---

## 🔧 核心功能详解

### ⭐ 功能 1：日记详情独立 URL（模态框形式）

**点击流程**：
```vue
<!-- DiaryPanel.vue -->
<div @click="router.push(`/diary/${diary.id}`)">
  <h4>{{ diary.title }}</h4>
</div>
```

**App.vue 监听路由**：
```vue
<script setup>
watch(() => route.name, (newName) => {
  if (newName === 'DiaryDetail') {
    currentDiaryId.value = Number(route.params.id)
    showDiaryDetail.value = true  // 打开模态框
  }
})
</script>

<template>
  <!-- 全局模态框 -->
  <DiaryDetailModal
    v-model:show="showDiaryDetail"
    :diary-id="currentDiaryId"
  />
</template>
```

**效果**：
- ✅ URL 变为 `/#/diary/25`
- ✅ 模态框覆盖整个页面（保持原有样式）
- ✅ 点击遮罩或关闭按钮 → `router.back()` → 返回列表
- ✅ 可以直接分享 `/#/diary/25` 给他人

### ⭐ 功能 2：登录模态框（查询参数触发）

**点击流程**：
```vue
<!-- UserPanel.vue -->
<button @click="router.push({ query: { login: 'true' } })">
  登录 / 注册
</button>
```

**App.vue 监听查询参数**：
```vue
<script setup>
watch(() => route.query.login, (newVal) => {
  if (newVal === 'true') {
    showLogin.value = true  // 打开模态框
  }
})
</script>

<template>
  <AuthModal v-model:show="showLogin" />
</template>
```

**效果**：
- ✅ URL 变为 `/#/nav?login=true`
- ✅ 模态框覆盖整个页面
- ✅ 关闭模态框 → 移除 `?login=true` 参数
- ✅ 不影响当前页面（导航/日记列表等）

---

## 📱 完整交互流程

### 场景 1：查看日记详情

```
用户在 /#/diary (日记列表)
  ↓
点击某篇日记 (ID=25)
  ↓
URL 变为 /#/diary/25
  ↓
触发 App.vue 的路由监听
  ↓
showDiaryDetail = true
  ↓
DiaryDetailModal 以模态框形式显示（全屏覆盖）
  ↓
用户点击关闭按钮
  ↓
router.back()
  ↓
返回 /#/diary
```

### 场景 2：分享日记链接

```
用户复制 URL: http://domain.com/#/diary/25
  ↓
朋友打开链接
  ↓
App.vue 检测到 route.name === 'DiaryDetail'
  ↓
自动加载日记 ID=25
  ↓
模态框直接显示
```

### 场景 3：登录

```
用户点击「登录 / 注册」
  ↓
router.push({ query: { login: 'true' } })
  ↓
URL 变为 /#/nav?login=true
  ↓
App.vue 监听到 route.query.login === 'true'
  ↓
showLogin = true
  ↓
AuthModal 模态框显示
  ↓
登录成功
  ↓
模态框关闭，移除 ?login=true
  ↓
返回 /#/nav
```

---

## 🎯 开发者指南

### 1. 跳转到日记详情（触发模态框）

```javascript
import { useRouter } from 'vue-router'
const router = useRouter()

function viewDiary(id) {
  router.push(`/diary/${id}`)  // URL 变化 + 模态框显示
}
```

### 2. 触发登录模态框

```javascript
function showLogin() {
  router.push({ query: { login: 'true' } })
}
```

### 3. 在地图中跳转到日记

```vue
<!-- MapCanvas.vue -->
<script setup>
import { useRouter } from 'vue-router'
const router = useRouter()

function onMarkerClick(spot) {
  // 方式 1: 筛选该景点的日记列表
  router.push({ path: '/diary', query: { spotId: spot.id } })
  
  // 方式 2: 直接打开某篇日记的模态框
  router.push(`/diary/${diaryId}`)
}
</script>
```

---

## 🚀 启动项目

```bash
cd frontend
npm run dev
```

访问 http://localhost:5173 会自动重定向到 `#/nav`

---

## 🔗 URL 分享示例

所有链接都可以直接分享，打开后会自动显示对应的模态框：

```
# 分享日记（自动打开模态框）
http://yourdomain.com/#/diary/25

# 分享景点的日记列表
http://yourdomain.com/#/diary?spotId=5

# 分享带登录提示的页面
http://yourdomain.com/#/nav?login=true
```

---

## 📝 技术要点

### 1. 为什么不用 router-view 显示模态框？

**原因**：模态框需要覆盖整个页面（包括侧边栏 + 地图），而 router-view 只在侧边栏内部。

**解决方案**：
- 模态框组件在 `App.vue` 中声明（顶层）
- 通过监听路由变化来控制显示/隐藏
- 使用 `Teleport to="body"` 确保模态框覆盖整个页面

### 2. 路由参数 vs 查询参数

- **路由参数** (`/diary/:id`)：用于资源标识（日记 ID）
- **查询参数** (`?login=true`)：用于触发状态（打开模态框）

### 3. 关闭模态框的处理

```javascript
// DiaryDetailModal 关闭时
watch(showDiaryDetail, (newVal) => {
  if (!newVal && route.name === 'DiaryDetail') {
    router.back()  // 返回上一页
  }
})

// AuthModal 关闭时
watch(showLogin, (newVal) => {
  if (!newVal && route.query.login === 'true') {
    const query = { ...route.query }
    delete query.login
    router.replace({ query })  // 移除查询参数
  }
})
```

---

## ✨ 完成！

现在你的项目实现了：
- ✅ **保持原有 UI 交互** - 模态框仍然是全屏覆盖
- ✅ **每篇日记独立 URL** - 可分享、可收藏
- ✅ **登录独立 URL** - 可直接访问登录页
- ✅ **URL 驱动界面** - 支持浏览器历史记录
- ✅ **地图持久化** - 路由切换不影响地图状态

享受现代化的路由体验！🎉

---

## 🔧 核心功能详解

### ⭐ 功能 1：每篇日记独立 URL

**使用场景**：用户可以分享特定日记的链接

**实现方式**：
```vue
<!-- DiaryPanel.vue - 点击日记卡片 -->
<div @click="router.push(`/diary/${diary.id}`)">
  <h4>{{ diary.title }}</h4>
</div>
```

**URL 示例**：
```
/#/diary/1  → 查看 ID=1 的日记
/#/diary/99 → 查看 ID=99 的日记
```

**效果**：
- ✅ 每篇日记有独立 URL，可以分享给他人
- ✅ 浏览器前进/后退按钮可用
- ✅ 刷新页面后停留在当前日记详情
- ✅ 点击「返回」按钮回到日记列表

### ⭐ 功能 2：登录独立路由

**使用场景**：未登录用户访问需要权限的页面时，跳转到登录页

**实现方式**：
```vue
<!-- UserPanel.vue - 登录按钮 -->
<router-link to="/login" class="btn-primary">
  登录 / 注册
</router-link>
```

**特性**：
- ✅ 登录页面有独立 URL (`/#/login`)
- ✅ 登录成功后自动返回之前页面
- ✅ 已登录用户访问 `/login` 会自动跳转到首页
- ✅ 支持模态框和全屏两种显示模式

---

## 🎨 开发者指南

### 1. 跳转到日记详情

```javascript
// 方式 1：在模板中使用 router-link
<router-link :to="`/diary/${diary.id}`">
  查看详情
</router-link>

// 方式 2：在脚本中使用 router.push
import { useRouter } from 'vue-router'
const router = useRouter()

function viewDiary(id) {
  router.push(`/diary/${id}`)
}
```

### 2. 读取日记 ID 参数

```vue
<script setup>
import { useRoute } from 'vue-router'

const route = useRoute()
const diaryId = route.params.id  // 从 URL 读取 :id 参数

console.log('当前日记 ID:', diaryId)
</script>
```

### 3. 需要登录的路由（可选）

在 `router/index.js` 中添加 `meta.requiresAuth`：

```javascript
{
  path: '/my-diaries',
  component: () => import('./components/MyDiaries.vue'),
  meta: {
    requiresAuth: true  // 需要登录
  }
}
```

路由守卫会自动检查并跳转到登录页。

### 4. 在地图中跳转到日记详情

```vue
<!-- MapCanvas.vue -->
<script setup>
import { useRouter } from 'vue-router'
const router = useRouter()

function onMarkerClick(spot) {
  // 跳转到日记列表并筛选该景点
  router.push({ 
    path: '/diary', 
    query: { spotId: spot.id } 
  })
  
  // 或者直接跳转到某篇日记
  // router.push(`/diary/${diaryId}`)
}
</script>
```

---

## 🎯 URL 参数传递示例

### 场景 1：点击日记卡片 → 查看详情
```
用户在日记列表 (#/diary)
  ↓
点击 ID=5 的日记
  ↓
URL 变为 #/diary/5
  ↓
DiaryDetailModal 显示该日记
```

### 场景 2：点击景点标记 → 查看该景点的日记
```
用户点击地图上的景点 (ID=3)
  ↓
router.push({ path: '/diary', query: { spotId: 3 } })
  ↓
URL 变为 #/diary?spotId=3
  ↓
DiaryPanel 只显示景点 3 的日记
```

### 场景 3：未登录用户发表评论
```
用户点击「发表评论」
  ↓
检测到未登录
  ↓
router.push('/login')
  ↓
登录成功后返回原页面
```

---

## 📱 路由架构设计

### 持久化地图 + 动态内容面板

```
┌─────────────────────────────────────┐
│         App.vue (根组件)              │
│  ┌──────────┐  ┌──────────────────┐ │
│  │ Sidebar  │  │   MapCanvas      │ │
│  │ (固定)   │  │   (持久化)       │ │
│  │          │  │                  │ │
│  │ ┌──────┐ │  │   ChatPanel      │ │
│  │ │router│ │  │   (固定)         │ │
│  │ │-view │ │  │                  │ │
│  │ │(动态)│ │  │                  │ │
│  │ └──────┘ │  │                  │ │
│  └──────────┘  └──────────────────┘ │
└─────────────────────────────────────┘

router-view 根据 URL 显示：
- /#/nav         → NavigationPanel
- /#/diary       → DiaryPanel
- /#/diary/5     → DiaryDetailModal
- /#/login       → AuthModal
```

**优势**：
- ✅ 地图状态完全保留（不重新加载）
- ✅ 左侧面板根据 URL 切换
- ✅ 支持浏览器历史记录
- ✅ 可以分享精确的页面状态

---

## 🚀 启动项目

```bash
cd frontend
npm run dev
```

访问 http://localhost:5173 会自动重定向到 `#/nav`

---

## 🔗 分享链接示例

用户可以直接分享以下链接：

```
# 分享日记
http://yourdomain.com/#/diary/25

# 分享景点的日记列表
http://yourdomain.com/#/diary?spotId=5

# 分享登录页面（用于引导新用户）
http://yourdomain.com/#/login
```

---

## 📝 注意事项

1. **双模式组件**
   - `DiaryDetailModal` 和 `AuthModal` 支持两种模式
   - 作为路由视图：占据整个侧边栏面板
   - 作为模态框：浮层显示（向后兼容）

2. **路由参数 vs 查询参数**
   - 路由参数：`/diary/:id` → 用于资源标识（日记 ID）
   - 查询参数：`/diary?spotId=5` → 用于筛选条件

3. **返回导航**
   - 日记详情页：点击「← 返回」调用 `router.back()`
   - 登录页：点击「← 返回」跳转到 `/nav`

4. **权限检查**
   - 路由守卫在 `router/index.js` 中配置
   - 检测到 `meta.requiresAuth` 会自动跳转登录页

---

## ✨ 完成！

现在你的项目实现了：
- ✅ **每篇日记独立 URL** - 可分享、可收藏
- ✅ **登录独立路由** - 完整的登录流程
- ✅ **地图持久化** - 路由切换不影响地图状态
- ✅ **URL 驱动界面** - 支持浏览器历史记录

享受现代化的路由体验！🎉

---

## 🔧 开发者指南

### 1. 在组件中使用路由

#### 方式一：使用 router-link（推荐用于导航按钮）
```vue
<template>
  <router-link to="/nav" class="nav-button">
    导航
  </router-link>
  
  <!-- 带查询参数 -->
  <router-link :to="{ path: '/diary', query: { spotId: 123 } }">
    查看景点日记
  </router-link>
</template>
```

#### 方式二：编程式导航
```vue
<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()

function goToDiary(spotId) {
  router.push({ path: '/diary', query: { spotId } })
}

function goBack() {
  router.back()
}
</script>

<template>
  <button @click="goToDiary(5)">查看教学楼日记</button>
</template>
```

### 2. 读取 URL 参数

#### 在 MapCanvas.vue 中读取地图坐标
```vue
<script setup>
import { watch } from 'vue'
import { useRouteQueryNumber } from '@/composables/useRouteQuery'

// 读取 URL 中的 lat 和 lng 参数
const lat = useRouteQueryNumber('lat', 39.9609)  // 默认值：北邮纬度
const lng = useRouteQueryNumber('lng', 116.3587) // 默认值：北邮经度

// 监听参数变化，更新地图中心
watch([lat, lng], ([newLat, newLng]) => {
  console.log('地图中心更新:', newLat, newLng)
  // 调用地图 API 更新中心点
  map.setCenter([newLng, newLat])
})
</script>
```

#### 在 DiaryPanel.vue 中读取景点 ID
```vue
<script setup>
import { useRouteQueryNumber } from '@/composables/useRouteQuery'

// 自动从 URL 读取 spotId 参数
const spotId = useRouteQueryNumber('spotId', 0)

// spotId 会随 URL 变化自动更新
</script>
```

### 3. 高亮当前激活路由

路由自动添加 CSS 类：
- `.router-link-active` - 当前路由激活
- `.router-link-exact-active` - 精确匹配激活

在 Sidebar.vue 中已经实现：
```vue
<router-link
  to="/nav"
  :class="currentRoute === '/nav' ? 'text-bupt-blue' : 'text-gray-600'"
>
  导航
</router-link>
```

---

## 🎨 架构优势

### ✅ 地图组件持久化
- `MapCanvas` 在 `App.vue` 中声明，**不受路由切换影响**
- 切换导航/日记面板时，地图状态完全保留
- 避免重复加载地图资源，提升性能

### ✅ URL 驱动界面
```
用户点击「社区日记」
  ↓
URL 变更为 #/diary
  ↓
浏览器前进/后退按钮可用
  ↓
可以直接分享带参数的链接
```

### ✅ 懒加载优化
所有面板组件都是懒加载：
```javascript
component: () => import('../components/DiaryPanel.vue')
```
首屏只加载必要代码，提升加载速度。

---

## 🚀 启动项目

```bash
cd frontend
npm run dev
```

访问 http://localhost:5173 会自动重定向到 `#/nav`

---

## 🔗 URL 参数传递示例

### 场景 1：从地图点击景点跳转到日记
```javascript
// 在 MapCanvas.vue 中
function onMarkerClick(spot) {
  router.push({
    path: '/diary',
    query: { 
      spotId: spot.id,
      lat: spot.latitude,
      lng: spot.longitude
    }
  })
}

// URL 变为：#/diary?spotId=5&lat=39.96&lng=116.35
```

### 场景 2：分享景点链接
用户可以直接复制浏览器地址栏的 URL：
```
http://yourdomain.com/#/diary?spotId=5
```
其他人打开这个链接会直接看到该景点的日记。

---

## 📝 注意事项

1. **路由模式选择**
   - 当前使用 Hash 模式 (`createWebHashHistory`)
   - URL 格式：`http://domain.com/#/nav`
   - 无需服务器额外配置

2. **组件通信**
   - 面板组件通过 `emit` 向 Sidebar 发送事件
   - Sidebar 负责调用 `router.push` 进行路由跳转
   - URL 参数通过 `useRouteQuery` 读取

3. **Pinia 状态管理**
   - 保持原有逻辑不变
   - 路由只负责视图切换，不影响业务状态

---

## 🎯 下一步建议

### 可选扩展功能

1. **添加路由守卫（权限控制）**
```javascript
// router/index.js
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  if (to.meta.requiresAuth && !authStore.isLoggedIn) {
    next('/login')
  } else {
    next()
  }
})
```

2. **添加页面过渡动画**
```vue
<!-- App.vue -->
<router-view v-slot="{ Component }">
  <transition name="fade" mode="out-in">
    <component :is="Component" />
  </transition>
</router-view>
```

3. **路由历史记录管理**
```javascript
// 返回上一页
router.back()

// 替换当前历史记录（不会增加新记录）
router.replace('/nav')
```

---

## ✨ 完成！

现在你的项目已经成功集成 Vue Router，享受 URL 驱动的开发体验吧！🎉
