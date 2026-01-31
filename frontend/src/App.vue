<!--
  Vue 3 根组件
  应用的主要布局组件，包含侧边栏、地图区域、聊天面板
-->
<template>
  <div class="app-container">
    <!-- 左侧侧边栏：包含导航面板、日记面板、用户信息 -->
    <Sidebar />

    <!-- 右侧地图区域：地图画布 + AI聊天面板 -->
    <div class="map-area">
      <!-- 地图画布：显示校园地图、景点、导航路径 -->
      <MapCanvas />
      <!-- AI聊天面板：智能导游助手 -->
      <ChatPanel />
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import Sidebar from './components/Sidebar.vue'
import MapCanvas from './components/MapCanvas.vue'
import ChatPanel from './components/ChatPanel.vue'
import { useMapStore } from './stores/map'

// 获取地图状态管理实例
const mapStore = useMapStore()

// 组件挂载后初始化
onMounted(() => {
  // 应用启动时立即加载地图图数据
  // 包括节点（景点）、边（路径）信息
  mapStore.loadGraph()
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
