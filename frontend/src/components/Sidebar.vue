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

        <!-- Tab 切换 - 现代药丸风格（使用 router-link） -->
        <div class="px-4 pt-4">
          <div class="relative bg-gray-100/70 backdrop-blur-sm rounded-xl p-1 flex gap-1">
            <!-- 滑动背景 -->
            <div 
              class="absolute top-1 bottom-1 bg-white rounded-lg shadow-md transition-all duration-300 ease-out"
              :style="{ 
                left: currentRoute === '/nav' ? '4px' : '50%',
                right: currentRoute === '/diary' ? '4px' : '50%'
              }"
            ></div>
            
            <router-link
              to="/nav"
              class="relative z-10 flex-1 py-2.5 px-4 rounded-lg font-medium text-sm transition-all duration-200 active:scale-95"
              :class="currentRoute === '/nav' ? 'text-bupt-blue' : 'text-gray-600 hover:text-gray-900'"
            >
              <div class="flex items-center justify-center gap-2">
                <Navigation :size="16" />
                <span>导航</span>
              </div>
            </router-link>
            
            <router-link
              to="/diary"
              class="relative z-10 flex-1 py-2.5 px-4 rounded-lg font-medium text-sm transition-all duration-200 active:scale-95"
              :class="currentRoute === '/diary' ? 'text-bupt-blue' : 'text-gray-600 hover:text-gray-900'"
            >
              <div class="flex items-center justify-center gap-2">
                <BookOpen :size="16" />
                <span>社区日记</span>
              </div>
            </router-link>
          </div>
        </div>

        <!-- 内容区域 - 路由视图替代原来的条件渲染 -->
        <div class="flex-1 overflow-hidden px-4 py-4">
          <div class="h-full overflow-y-auto custom-scrollbar">
            <Transition name="tab-fade" mode="out-in">
              <router-view 
                :spot-id="selectedSpotId" 
                @view-spot-diaries="handleViewSpotDiaries"
                @clear-spot-filter="handleClearSpotFilter"
              />
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
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Menu, Navigation, BookOpen } from 'lucide-vue-next'
import UserPanel from './UserPanel.vue'

const router = useRouter()
const route = useRoute()

const isOpen = ref(true)
const selectedSpotId = ref(null)

// 计算当前路由路径
const currentRoute = computed(() => route.path)

function toggleSidebar() {
  isOpen.value = !isOpen.value
}

/**
 * 处理从景点查看日记的跳转
 * @param {number} spotId - 景点ID
 */
function handleViewSpotDiaries(spotId) {
  selectedSpotId.value = spotId
  // 使用路由导航，同时传递查询参数
  router.push({ 
    path: '/diary', 
    query: { spotId: spotId.toString() } 
  })
}

/**
 * 清除景点筛选
 */
function handleClearSpotFilter() {
  selectedSpotId.value = null
  // 清除查询参数
  router.push({ path: '/diary' })
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
