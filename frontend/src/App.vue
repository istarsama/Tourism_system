<!--
  Vue 3 根组件
  应用的主要布局组件，包含侧边栏、地图区域、聊天面板
  
  架构设计：
  - MapCanvas 在 router-view 之外，确保地图组件不会因路由切换而重新挂载
  - Sidebar 通过 router-view 动态加载不同的功能面板
  - 全局模态框通过监听路由参数控制显示
-->
<template>
  <div class="app-container">
    <!-- 左侧侧边栏：包含路由视图（导航/日记/用户面板） -->
    <Sidebar />

    <!-- 右侧地图区域：地图画布 + AI聊天面板 -->
    <div class="map-area">
      <!-- 地图画布：显示校园地图、景点、导航路径（持久化组件，不会卸载） -->
      <MapCanvas />
      <!-- AI聊天面板：智能导游助手 -->
      <ChatPanel />
    </div>

    <!-- 全局模态框：通过路由参数控制显示 -->
    <!-- 日记详情模态框 -->
    <DiaryDetailModal
      v-model:show="showDiaryDetail"
      :diary-id="currentDiaryId"
    />

    <!-- 登录模态框 -->
    <AuthModal v-model:show="showLogin" />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Sidebar from './components/Sidebar.vue'
import MapCanvas from './components/MapCanvas.vue'
import ChatPanel from './components/ChatPanel.vue'
import DiaryDetailModal from './components/DiaryDetailModal.vue'
import AuthModal from './components/AuthModal.vue'
import { useMapStore } from './stores/map'

// 获取地图状态管理实例
const mapStore = useMapStore()
const route = useRoute()
const router = useRouter()

// 日记详情模态框控制
const showDiaryDetail = ref(false)
const currentDiaryId = ref(null)

// 登录模态框控制
const showLogin = ref(false)

// 监听路由名称变化，控制日记详情模态框
watch(() => route.name, (newName) => {
  if (newName === 'DiaryDetail') {
    currentDiaryId.value = Number(route.params.id)
    showDiaryDetail.value = true
  } else {
    showDiaryDetail.value = false
  }
})

// 监听 login 查询参数变化，控制登录模态框
watch(() => route.query.login, (loginParam) => {
  showLogin.value = loginParam === 'true'
})

// 监听日记 ID 参数变化
watch(() => route.params.id, (newId) => {
  if (route.name === 'DiaryDetail' && newId) {
    currentDiaryId.value = Number(newId)
    showDiaryDetail.value = true
  }
})

// 监听模态框关闭，返回上一页
watch(showDiaryDetail, (newVal) => {
  if (!newVal && route.name === 'DiaryDetail') {
    router.back()
  }
})

watch(showLogin, (newVal) => {
  if (!newVal && route.query.login === 'true') {
    // 移除 login 查询参数
    const query = { ...route.query }
    delete query.login
    router.replace({ query })
  }
})

// 组件挂载后初始化
onMounted(() => {
  // 应用启动时立即加载地图数据
  // 包括节点（景点）、边（路径）信息
  mapStore.loadGraph()

  // 检查初始路由状态
  if (route.name === 'DiaryDetail') {
    currentDiaryId.value = Number(route.params.id)
    showDiaryDetail.value = true
  }
  if (route.query.login === 'true') {
    showLogin.value = true
  }
})
</script>

<style scoped>
/* 应用容器：全屏布局 */
.app-container {
  display: flex;
  height: 100vh;  /* 视口高度 */
  overflow: hidden; /* 防止内容溢出 */
}

/* 地图区域：占据剩余空间 */
.map-area {
  flex: 1;  /* 占据剩余宽度 */
  position: relative;
  overflow: hidden; /* 子元素超出时隐藏 */
}
</style>
