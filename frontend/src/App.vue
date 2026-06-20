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
      <MapCanvas v-if="mapStore.activeScope === 'campus'" />
      <IndoorMapView v-else-if="mapStore.activeScope === 'indoor'" />
      <NationalMapView v-else />
      <!-- AI聊天面板：智能导游助手 -->
      <ChatPanel />
    </div>
  </div>
</template>

<script setup>
import Sidebar from './components/Sidebar.vue'
import MapCanvas from './components/MapCanvas.vue'
import IndoorMapView from './components/IndoorMapView.vue'
import NationalMapView from './components/NationalMapView.vue'
import ChatPanel from './components/ChatPanel.vue'
import { useMapStore } from './stores/map'

// 获取地图状态管理实例
const mapStore = useMapStore()
</script>

<style scoped>
/* 应用容器：全屏布局 */
.app-container {
  display: flex;
  position: relative;
  isolation: isolate;
  width: 100vw;
  height: 100vh;  /* 视口高度 */
  overflow: hidden; /* 防止内容溢出 */
}

/* 地图区域：占据剩余空间 */
.map-area {
  flex: 1;  /* 占据剩余宽度 */
  min-width: 0;
  position: relative;
  z-index: 0;
  overflow: hidden; /* 子元素超出时隐藏 */
}
</style>


