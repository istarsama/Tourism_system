<template>
  <!-- 侧边栏主体 - Glassmorphism 风格 -->
  <Transition name="sidebar-slide">
    <div 
      v-if="isOpen"
      v-motion
      :initial="{ opacity: 0, x: -100 }"
      :enter="{ opacity: 1, x: 0, transition: { duration: 600 } }"
      class="fixed left-4 top-4 bottom-4 w-[380px] z-10"
    >
      <div class="h-full bg-white/70 backdrop-blur-md rounded-2xl shadow-2xl ring-1 ring-black/5 flex flex-col overflow-hidden">
        <!-- 头部 - 北邮蓝渐变 -->
        <div class="relative px-6 py-5 bg-gradient-to-r from-bupt-blue to-bupt-blue-light">
          <div class="flex items-center gap-3">
            <div class="w-12 h-12 rounded-xl overflow-hidden ring-2 ring-white/50 shadow-lg">
              <img src="/logo.jpg" alt="logo" class="w-full h-full object-cover">
            </div>
            <div>
              <h1 class="text-xl font-bold text-white tracking-wide">校园导游</h1>
              <p class="text-xs text-white/80 mt-0.5">Campus Navigator</p>
            </div>
          </div>
          
          <!-- 装饰性渐变 -->
          <div class="absolute inset-0 bg-gradient-to-br from-white/10 to-transparent pointer-events-none"></div>
        </div>

        <!-- 用户信息面板 -->
        <div class="px-4 pt-4">
          <UserPanel />
        </div>

        <!-- Tab 切换 - 现代药丸风格 -->
        <div class="px-4 pt-4">
          <div class="relative bg-gray-100/70 backdrop-blur-sm rounded-xl p-1 flex gap-1">
            <!-- 滑动背景 -->
            <div 
              class="absolute top-1 bottom-1 bg-white rounded-lg shadow-md transition-all duration-300 ease-out"
              :style="{ 
                left: activeTab === 'nav' ? '4px' : '50%',
                right: activeTab === 'diary' ? '4px' : '50%'
              }"
            ></div>
            
            <button 
              @click="activeTab = 'nav'"
              class="relative z-10 flex-1 py-2.5 px-4 rounded-lg font-medium text-sm transition-all duration-200 active:scale-95"
              :class="activeTab === 'nav' ? 'text-bupt-blue' : 'text-gray-600 hover:text-gray-900'"
            >
              <div class="flex items-center justify-center gap-2">
                <Navigation :size="16" />
                <span>导航</span>
              </div>
            </button>
            
            <button 
              @click="activeTab = 'diary'"
              class="relative z-10 flex-1 py-2.5 px-4 rounded-lg font-medium text-sm transition-all duration-200 active:scale-95"
              :class="activeTab === 'diary' ? 'text-bupt-blue' : 'text-gray-600 hover:text-gray-900'"
            >
              <div class="flex items-center justify-center gap-2">
                <BookOpen :size="16" />
                <span>社区日记</span>
              </div>
            </button>
          </div>
        </div>

        <!-- 内容区域 - 带过渡动画 -->
        <div class="flex-1 overflow-hidden px-4 py-4">
          <div class="h-full overflow-y-auto custom-scrollbar">
            <Transition name="tab-fade" mode="out-in">
              <div v-if="activeTab === 'nav'" key="nav">
                <NavigationPanel @view-spot-diaries="handleViewSpotDiaries" />
              </div>
              <div v-else key="diary">
                <DiaryPanel :spot-id="selectedSpotId" @clear-spot-filter="handleClearSpotFilter" />
              </div>
            </Transition>
          </div>
        </div>
      </div>
    </div>
  </Transition>

  <!-- 侧边栏切换按钮 - 固定定位 -->
  <button 
    @click="toggleSidebar" 
    class="fixed top-4 z-[100] bg-white/80 backdrop-blur-md hover:bg-white/90 rounded-xl p-3 shadow-lg ring-1 ring-black/5 active:scale-95 hover:shadow-xl"
    :class="isOpen ? 'left-[352px]' : 'left-6'"
    style="transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);"
    :title="isOpen ? '收起侧边栏' : '打开侧边栏'"
  >
    <Menu :size="20" class="text-bupt-blue" />
  </button>
</template>

<script setup>
import { ref } from 'vue'
import { Menu, Navigation, BookOpen } from 'lucide-vue-next'
import UserPanel from './UserPanel.vue'
import NavigationPanel from './NavigationPanel.vue'
import DiaryPanel from './DiaryPanel.vue'

const isOpen = ref(true)
const activeTab = ref('nav')
const selectedSpotId = ref(null)

function toggleSidebar() {
  isOpen.value = !isOpen.value
}

function handleViewSpotDiaries(spotId) {
  selectedSpotId.value = spotId
  activeTab.value = 'diary'
}

function handleClearSpotFilter() {
  selectedSpotId.value = null
}
</script>

<style scoped>
/* 北邮蓝色系 */
:root {
  --bupt-blue: #003d74;
  --bupt-blue-light: #0056a3;
  --mint-green: #10b981;
}

/* 自定义滚动条 */
.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}

.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(0, 61, 116, 0.2);
  border-radius: 3px;
}

.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 61, 116, 0.4);
}

/* 侧边栏滑入动画 */
.sidebar-slide-enter-active,
.sidebar-slide-leave-active {
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.sidebar-slide-enter-from,
.sidebar-slide-leave-to {
  opacity: 0;
  transform: translateX(-100%);
}

/* Tab 内容切换动画 */
.tab-fade-enter-active,
.tab-fade-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.tab-fade-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.tab-fade-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}
</style>
