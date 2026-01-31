<template>
  <div class="space-y-4">
    <!-- 路径选择卡片 - Glassmorphism -->
    <div class="bg-gradient-to-br from-white/80 to-white/60 backdrop-blur-sm rounded-2xl p-5 ring-1 ring-black/5 shadow-lg">
      <!-- 起点选择 -->
      <div class="space-y-2">
        <label class="flex items-center gap-2 text-sm font-semibold text-gray-700">
          <div class="w-3 h-3 rounded-full bg-green-500 ring-2 ring-green-200"></div>
          起点
        </label>
        <SearchInput
          v-model="startSearch"
          placeholder="点击地图或搜索景点..."
          :selected="mapStore.startNode"
          @select="handleSelectStart"
        />
      </div>

      <!-- 起终点切换按钮 - 带旋转动画 -->
      <div class="flex justify-center -my-2 relative z-10">
        <button
          @click="handleSwapPoints"
          :disabled="!mapStore.startNode || !mapStore.endNode"
          class="bg-white/90 backdrop-blur-sm rounded-full p-2.5 shadow-md ring-1 ring-black/5 
                 hover:shadow-lg hover:scale-110 active:scale-95 
                 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:scale-100
                 transition-all duration-300 group"
        >
          <ArrowDownUp 
            :size="18" 
            class="text-bupt-blue transition-transform duration-500 group-hover:rotate-180" 
          />
        </button>
      </div>

      <!-- 终点选择 -->
      <div class="space-y-2">
        <label class="flex items-center gap-2 text-sm font-semibold text-gray-700">
          <div class="w-3 h-3 rounded-full bg-red-500 ring-2 ring-red-200"></div>
          终点
        </label>
        <SearchInput
          v-model="endSearch"
          placeholder="点击地图或搜索景点..."
          :selected="mapStore.endNode"
          @select="handleSelectEnd"
        />
      </div>

      <!-- 导航选项 -->
      <div class="grid grid-cols-2 gap-3 mt-4 pt-4 border-t border-gray-200/50">
        <!-- 导航策略 -->
        <div class="space-y-1.5">
          <label class="text-xs font-medium text-gray-600 flex items-center gap-1">
            <Route :size="14" />
            策略
          </label>
          <select 
            v-model="strategy"
            class="w-full px-3 py-2 bg-white/70 backdrop-blur-sm border border-gray-200/50 rounded-lg text-sm
                   focus:border-bupt-blue focus:ring-2 focus:ring-bupt-blue/20 focus:outline-none
                   transition-all duration-200"
          >
            <option value="dist">最短距离</option>
            <option value="time">最少时间</option>
          </select>
        </div>

        <!-- 出行方式 -->
        <div class="space-y-1.5">
          <label class="text-xs font-medium text-gray-600 flex items-center gap-1">
            <Car :size="14" />
            方式
          </label>
          <select 
            v-model="transport"
            class="w-full px-3 py-2 bg-white/70 backdrop-blur-sm border border-gray-200/50 rounded-lg text-sm
                   focus:border-bupt-blue focus:ring-2 focus:ring-bupt-blue/20 focus:outline-none
                   transition-all duration-200"
          >
            <option value="walk">🚶 步行</option>
            <option value="bike">🚲 自行车</option>
          </select>
        </div>
      </div>

      <!-- 操作按钮组 -->
      <div class="grid grid-cols-2 gap-2 mt-4">
        <button 
          @click="handleNavigate"
          :disabled="!mapStore.canNavigate || isNavigating"
          class="px-4 py-2.5 bg-gradient-to-r from-bupt-blue to-bupt-blue-light text-white rounded-xl font-medium text-sm
                 shadow-lg shadow-bupt-blue/30 hover:shadow-xl hover:shadow-bupt-blue/40 hover:-translate-y-0.5
                 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:translate-y-0
                 transition-all duration-200 flex items-center justify-center gap-2"
        >
          <component :is="isNavigating ? Loader2 : Navigation" :size="16" :class="{ 'animate-spin': isNavigating }" />
          {{ isNavigating ? '规划中' : '开始导航' }}
        </button>
        
        <button 
          @click="handleReset"
          class="px-4 py-2.5 bg-white/70 backdrop-blur-sm text-gray-700 rounded-xl font-medium text-sm
                 ring-1 ring-gray-200/50 hover:bg-white/90 hover:ring-gray-300
                 active:scale-95 transition-all duration-200 flex items-center justify-center gap-2"
        >
          <RotateCcw :size="16" />
          重置
        </button>
      </div>
    </div>

    <!-- 导航结果卡片 - 带入场动画 -->
    <Transition
      enter-active-class="transition-all duration-300 ease-out"
      enter-from-class="opacity-0 transform translate-y-4"
      leave-active-class="transition-all duration-200 ease-in"
      leave-to-class="opacity-0 transform -translate-y-2"
    >
      <div v-if="mapStore.hasPath" class="bg-gradient-to-br from-blue-50/80 to-indigo-50/60 backdrop-blur-sm rounded-2xl p-5 ring-1 ring-blue-200/50 shadow-lg">
        <div class="flex items-center gap-2 mb-3">
          <div class="p-2 bg-bupt-blue/10 rounded-lg">
            <MapIcon :size="18" class="text-bupt-blue" />
          </div>
          <h3 class="text-base font-bold text-bupt-blue">导航结果</h3>
        </div>
        
        <!-- 导航信息 -->
        <div class="bg-white/60 backdrop-blur-sm rounded-xl p-3 mb-3">
          <div class="flex items-center justify-between">
            <span class="text-sm text-gray-600">总消耗</span>
            <span class="text-lg font-bold text-bupt-blue">
              {{ mapStore.totalCost }} {{ mapStore.costUnit }}
            </span>
          </div>
        </div>
        
        <!-- 路径列表 -->
        <div class="space-y-2">
          <div class="flex items-center gap-2 text-sm font-semibold text-gray-700">
            <ListOrdered :size="16" />
            途径路线
          </div>
          <div class="bg-white/60 backdrop-blur-sm rounded-xl p-3 max-h-48 overflow-y-auto custom-scrollbar">
            <TransitionGroup name="path-item" tag="ol" class="space-y-2">
              <li 
                v-for="(id, index) in mapStore.currentPath" 
                :key="id"
                class="flex items-start gap-2 text-sm"
              >
                <span class="flex-shrink-0 w-5 h-5 rounded-full bg-bupt-blue/10 text-bupt-blue flex items-center justify-center text-xs font-semibold">
                  {{ index + 1 }}
                </span>
                <span class="text-gray-700 pt-0.5">{{ mapStore.nodeMap[id]?.name || `节点${id}` }}</span>
              </li>
            </TransitionGroup>
          </div>
        </div>
      </div>
    </Transition>

    <!-- 景点详情卡片 -->
    <Transition
      enter-active-class="transition-all duration-300 ease-out"
      enter-from-class="opacity-0 transform translate-y-4"
      leave-active-class="transition-all duration-200 ease-in"
      leave-to-class="opacity-0 transform -translate-y-2"
    >
      <div v-if="mapStore.selectedSpot" class="bg-gradient-to-br from-mint-green/10 to-emerald-50/60 backdrop-blur-sm rounded-2xl p-5 ring-1 ring-mint-green/20 shadow-lg">
        <div class="flex items-center gap-2 mb-3">
          <div class="p-2 bg-mint-green/10 rounded-lg">
            <MapPin :size="18" class="text-mint-green" />
          </div>
          <h3 class="text-base font-bold text-gray-800">景点详情</h3>
        </div>
        
        <div class="space-y-3">
          <div>
            <h4 class="text-lg font-bold text-gray-900 mb-1">{{ mapStore.selectedSpot.name }}</h4>
            <span class="inline-block px-2.5 py-1 bg-mint-green/10 text-mint-green text-xs font-semibold rounded-full">
              {{ mapStore.selectedSpot.category }}
            </span>
          </div>
          
          <p class="text-sm text-gray-700 leading-relaxed bg-white/50 rounded-lg p-3">
            {{ mapStore.selectedSpot.description }}
          </p>
          
          <button 
            v-if="authStore.isAuthenticated"
            @click="$emit('view-spot-diaries', mapStore.selectedSpot.id)"
            class="w-full px-4 py-2.5 bg-gradient-to-r from-mint-green to-emerald-500 text-white rounded-xl font-medium text-sm
                   shadow-lg shadow-mint-green/30 hover:shadow-xl hover:shadow-mint-green/40 hover:-translate-y-0.5
                   active:scale-95 transition-all duration-200 flex items-center justify-center gap-2"
          >
            <BookOpen :size="16" />
            查看该景点日记
          </button>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { 
  Navigation, Route, Car, MapIcon, MapPin, ArrowDownUp, 
  RotateCcw, Loader2, ListOrdered, BookOpen 
} from 'lucide-vue-next'
import { useMapStore } from '../stores/map'
import { useAuthStore } from '../stores/auth'
import SearchInput from './SearchInput.vue'

const mapStore = useMapStore()
const authStore = useAuthStore()

const startSearch = ref('')
const endSearch = ref('')
const strategy = ref('dist')
const transport = ref('walk')
const isNavigating = ref(false)

defineEmits(['view-spot-diaries'])

function handleSelectStart(spot) {
  mapStore.setStart(spot)
  startSearch.value = spot.name
}

function handleSelectEnd(spot) {
  mapStore.setEnd(spot)
  endSearch.value = spot.name
}

function handleSwapPoints() {
  if (!mapStore.startNode || !mapStore.endNode) return
  
  const tempStart = mapStore.startNode
  const tempStartSearch = startSearch.value
  
  mapStore.setStart(mapStore.endNode)
  mapStore.setEnd(tempStart)
  
  startSearch.value = endSearch.value
  endSearch.value = tempStartSearch
}

async function handleNavigate() {
  isNavigating.value = true
  try {
    await mapStore.navigate(strategy.value, transport.value)
  } catch (error) {
    alert('导航失败: ' + error.message)
  } finally {
    isNavigating.value = false
  }
}

function handleReset() {
  mapStore.resetNavigation()
  startSearch.value = ''
  endSearch.value = ''
}
</script>

<style scoped>
/* 北邮蓝色系 */
.bg-bupt-blue {
  background-color: #003d74;
}

.text-bupt-blue {
  color: #003d74;
}

.from-bupt-blue {
  --tw-gradient-from: #003d74;
}

.to-bupt-blue-light {
  --tw-gradient-to: #0056a3;
}

.border-bupt-blue {
  border-color: #003d74;
}

.ring-bupt-blue\/20 {
  --tw-ring-color: rgba(0, 61, 116, 0.2);
}

.shadow-bupt-blue\/30 {
  --tw-shadow-color: rgba(0, 61, 116, 0.3);
  --tw-shadow: var(--tw-shadow-colored);
}

.shadow-bupt-blue\/40 {
  --tw-shadow-color: rgba(0, 61, 116, 0.4);
  --tw-shadow: var(--tw-shadow-colored);
}

.bg-mint-green\/10 {
  background-color: rgba(16, 185, 129, 0.1);
}

.text-mint-green {
  color: #10b981;
}

.from-mint-green {
  --tw-gradient-from: #10b981;
}

.ring-mint-green\/20 {
  --tw-ring-color: rgba(16, 185, 129, 0.2);
}

.shadow-mint-green\/30 {
  --tw-shadow-color: rgba(16, 185, 129, 0.3);
  --tw-shadow: var(--tw-shadow-colored);
}

.shadow-mint-green\/40 {
  --tw-shadow-color: rgba(16, 185, 129, 0.4);
  --tw-shadow: var(--tw-shadow-colored);
}

/* 自定义滚动条 */
.custom-scrollbar::-webkit-scrollbar {
  width: 4px;
}

.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(0, 61, 116, 0.2);
  border-radius: 2px;
}

.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 61, 116, 0.4);
}

/* 路径项动画 */
.path-item-enter-active {
  transition: all 0.3s ease;
}

.path-item-enter-from {
  opacity: 0;
  transform: translateX(-20px);
}

.path-item-move {
  transition: transform 0.3s ease;
}
</style>
