<template>
  <div
    class="fixed left-4 top-4 bottom-4 z-[1200] sidebar-shell"
    :class="{ 'sidebar-shell-collapsed': !isOpen }"
  >
    <Transition name="sidebar-content-fade">
      <div
        v-show="isOpen"
        class="h-full bg-white/70 backdrop-blur-md rounded-2xl shadow-2xl ring-1 ring-black/5 flex flex-col overflow-hidden sidebar-content"
      >
        <!-- 头部 - 北邮蓝渐变 -->
        <div class="relative px-6 py-5 bg-gradient-to-r from-bupt-blue to-bupt-blue-light">
          <div class="flex items-center justify-between gap-3">
            <div class="flex items-center gap-3">
              <div class="w-12 h-12 rounded-xl overflow-hidden ring-2 ring-white/50 shadow-lg">
                <img src="/logo.jpg" alt="logo" class="w-full h-full object-cover">
              </div>
              <div>
                <h1 class="text-xl font-bold text-white tracking-wide">校园导游</h1>
                <p class="text-xs text-white/80 mt-0.5">Campus Navigator</p>
              </div>
            </div>
            <button
              @click="toggleSidebar"
              class="relative z-20 bg-white/20 hover:bg-white/30 text-white rounded-xl p-2.5 ring-1 ring-white/30 shadow-md active:scale-95 transition-all duration-200"
              title="收起侧边栏"
            >
              <Menu :size="18" />
            </button>
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
              @click="switchTab('nav')"
              class="relative z-10 flex-1 py-2.5 px-4 rounded-lg font-medium text-sm transition-all duration-200 active:scale-95"
              :class="activeTab === 'nav' ? 'text-bupt-blue' : 'text-gray-600 hover:text-gray-900'"
            >
              <div class="flex items-center justify-center gap-2">
                <Navigation :size="16" />
                <span>导航</span>
              </div>
            </button>

            <button
              @click="switchTab('diary')"
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
                <div class="mb-3 bg-white/70 backdrop-blur-sm rounded-xl p-1 flex gap-1 ring-1 ring-black/5">
                  <button
                    class="flex-1 py-2 px-3 rounded-lg text-xs font-semibold transition-all duration-200"
                    :class="mapStore.activeScope === 'campus'
                      ? 'bg-bupt-blue text-white shadow'
                      : 'text-gray-600 hover:text-gray-900'"
                    @click="switchMapScope('campus')"
                  >
                    校园地图
                  </button>
                  <button
                    class="flex-1 py-2 px-3 rounded-lg text-xs font-semibold transition-all duration-200"
                    :class="mapStore.activeScope === 'national'
                      ? 'bg-bupt-blue text-white shadow'
                      : 'text-gray-600 hover:text-gray-900'"
                    @click="switchMapScope('national')"
                  >
                    校外 OSM
                  </button>
                </div>
                <NavigationPanel
                  v-if="mapStore.activeScope === 'campus'"
                  @view-spot-diaries="handleViewSpotDiaries"
                />
                <NationalNavigationPanel v-else />
              </div>
              <div v-else key="diary">
                <DiaryPanel :spot-id="selectedSpotId" @clear-spot-filter="handleClearSpotFilter" />
              </div>
            </Transition>
          </div>
        </div>
      </div>
    </Transition>

    <div class="sidebar-rail" :class="{ 'sidebar-rail-visible': !isOpen }">
      <button
        @click="toggleSidebar"
        class="bg-white/85 backdrop-blur-md hover:bg-white/95 text-bupt-blue rounded-xl p-2.5 shadow-lg ring-1 ring-black/5 active:scale-95 transition-all duration-200"
        title="展开侧边栏"
      >
        <Menu :size="18" />
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Menu, Navigation, BookOpen } from 'lucide-vue-next'
import UserPanel from './UserPanel.vue'
import NavigationPanel from './NavigationPanel.vue'
import NationalNavigationPanel from './NationalNavigationPanel.vue'
import DiaryPanel from './DiaryPanel.vue'
import { useMapStore } from '../stores/map'

const isOpen = ref(true)
const route = useRoute()
const router = useRouter()
const mapStore = useMapStore()
const activeTab = computed(() => (route.name === 'Diary' ? 'diary' : 'nav'))
const selectedSpotId = computed(() => {
  const spotId = Number(route.query.spotId)
  return Number.isInteger(spotId) && spotId > 0 ? spotId : null
})

watch(
  () => route.query.scope,
  (scope) => {
    if (scope === 'campus' || scope === 'national') {
      if (scope !== mapStore.activeScope) {
        mapStore.setActiveScope(scope)
      }
      return
    }
    router.replace({
      name: route.name === 'Diary' ? 'Diary' : 'Navigation',
      query: {
        ...route.query,
        scope: mapStore.activeScope
      }
    })
  },
  { immediate: true }
)

watch(
  () => mapStore.activeScope,
  (scope) => {
    if (route.query.scope === scope) return
    router.replace({
      name: route.name === 'Diary' ? 'Diary' : 'Navigation',
      query: {
        ...route.query,
        scope
      }
    })
  }
)

function toggleSidebar() {
  isOpen.value = !isOpen.value
}

function handleViewSpotDiaries(spotId) {
  mapStore.setActiveScope('campus')
  router.push({
    name: 'Diary',
    query: {
      scope: 'campus',
      spotId: String(spotId)
    }
  })
}

function handleClearSpotFilter() {
  router.replace({
    name: 'Diary',
    query: {
      scope: mapStore.activeScope
    }
  })
}

function switchMapScope(scope) {
  mapStore.setActiveScope(scope)
  router.replace({
    name: route.name === 'Diary' ? 'Diary' : 'Navigation',
    query: {
      scope
    }
  })
}

function switchTab(tab) {
  const query = { scope: mapStore.activeScope }
  if (tab === 'diary' && selectedSpotId.value) {
    query.spotId = String(selectedSpotId.value)
  }
  router.push({
    name: tab === 'diary' ? 'Diary' : 'Navigation',
    query
  })
}
</script>

<style scoped>
/* 北邮蓝色系 */
:root {
  --bupt-blue: #003d74;
  --bupt-blue-light: #0056a3;
  --mint-green: #10b981;
}

.bg-bupt-blue {
  background-color: #003d74;
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

.sidebar-shell {
  width: 380px;
  overflow: hidden;
  transition: width 0.35s cubic-bezier(0.4, 0, 0.2, 1), transform 0.35s cubic-bezier(0.4, 0, 0.2, 1);
}

.sidebar-shell-collapsed {
  width: 52px;
}

.sidebar-content {
  min-width: 380px;
}

.sidebar-content-fade-enter-active,
.sidebar-content-fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.sidebar-content-fade-enter-from,
.sidebar-content-fade-leave-to {
  opacity: 0;
  transform: translateX(-10px);
}

.sidebar-rail {
  position: absolute;
  top: 14px;
  left: 8px;
  opacity: 0;
  pointer-events: none;
  transform: translateX(-8px);
  transition: opacity 0.2s ease, transform 0.25s ease;
}

.sidebar-rail-visible {
  opacity: 1;
  transform: translateX(0);
  pointer-events: auto;
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
