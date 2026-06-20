<template>
  <div class="space-y-4">
    <div class="bg-gradient-to-br from-white/80 to-white/60 backdrop-blur-sm rounded-2xl p-5 ring-1 ring-black/5 shadow-lg">
      <div class="flex items-center justify-between mb-3">
        <h3 class="text-sm font-bold text-gray-800">校外导航（OSM）</h3>
        <button class="text-xs text-bupt-blue font-semibold" @click="handleReload">刷新配置</button>
      </div>

      <div v-if="store.modeLoading || store.spotsLoading" class="text-sm text-gray-600">正在加载校外地图配置...</div>
      <div v-else-if="store.modeError" class="text-sm text-red-600">地图配置加载失败：{{ store.modeError }}</div>
      <div v-else-if="store.modeConfig && !store.supportsSlippyMap" class="text-sm text-amber-600">后端返回未启用 slippy map，暂不可用。</div>
      <div v-else-if="store.spotsError" class="text-sm text-red-600">全国景点加载失败：{{ store.spotsError }}</div>
      <div v-else-if="!store.hasSpots" class="text-sm text-gray-500">暂无全国景点数据。</div>

      <template v-else>
        <div class="space-y-3">
          <div>
            <label class="block text-xs font-semibold text-gray-600 mb-1">起点景点</label>
            <select :value="store.startSpot?.id || ''" class="select" @change="handleStartChange">
              <option value="">请选择起点</option>
              <option v-for="spot in startOptions" :key="spot.id" :value="spot.id">{{ spot.name }}（{{ spot.city }}）</option>
            </select>
          </div>

          <div>
            <label class="block text-xs font-semibold text-gray-600 mb-1">途径景点</label>
            <div class="flex gap-2">
              <select v-model="viaSelectId" class="select flex-1">
                <option value="">选择后添加</option>
                <option v-for="spot in viaOptions" :key="`via-${spot.id}`" :value="spot.id">{{ spot.name }}（{{ spot.city }}）</option>
              </select>
              <button class="small-btn" @click="handleAddVia">添加</button>
            </div>
            <div v-if="store.viaSpots.length" class="via-list">
              <div v-for="(spot, index) in store.viaSpots" :key="spot.id" class="via-item">
                <span>{{ index + 1 }}. {{ spot.name }}</span>
                <div class="flex gap-1">
                  <button class="icon-btn" :disabled="index === 0" @click="store.moveViaSpot(index, -1)">↑</button>
                  <button class="icon-btn" :disabled="index === store.viaSpots.length - 1" @click="store.moveViaSpot(index, 1)">↓</button>
                  <button class="icon-btn" @click="store.removeViaSpot(spot.id)">×</button>
                </div>
              </div>
            </div>
          </div>

          <div>
            <label class="block text-xs font-semibold text-gray-600 mb-1">终点景点</label>
            <select :value="store.endSpot?.id || ''" class="select" @change="handleEndChange">
              <option value="">请选择终点</option>
              <option v-for="spot in endOptions" :key="`end-${spot.id}`" :value="spot.id">{{ spot.name }}（{{ spot.city }}）</option>
            </select>
          </div>

          <p class="text-xs text-gray-500">
            支持同城多点串联
            <span v-if="constraintCity">（当前城市：{{ constraintCity }}）</span>
          </p>
          <p v-if="store.startSpot && store.endSpot && !store.sameCitySelected" class="text-xs text-amber-600">
            当前起点、途径点或终点不在同一城市，无法串联规划。
          </p>

          <div>
            <label class="block text-xs font-semibold text-gray-600 mb-1">交通方式</label>
            <select v-model="transport" class="select">
              <option value="walk">步行</option>
              <option value="bike">骑行</option>
            </select>
          </div>

          <div class="grid grid-cols-2 gap-2 pt-1">
            <button class="primary-btn" :disabled="!store.canNavigate || store.routeLoading" :title="store.canNavigateHint" @click="handleNavigate">
              {{ store.routeLoading ? '规划中...' : '开始多点导航' }}
            </button>
            <button class="reset-btn" @click="handleReset">重置</button>
          </div>

          <div v-if="store.routeError" class="text-xs text-red-600 pt-1">导航失败：{{ store.routeError }}</div>
        </div>
      </template>
    </div>

    <div class="bg-white/75 rounded-2xl p-4 ring-1 ring-black/5">
      <h4 class="text-sm font-bold text-gray-800 mb-2">城市景点推荐</h4>
      <div class="flex gap-2 mb-3">
        <input v-model="recommendCity" type="text" placeholder="输入城市，如北京、上海、杭州、西安" class="select" />
        <button class="small-btn" @click="applyCityFilter">推荐</button>
      </div>
      <div v-if="recommendedSpots.length" class="space-y-2">
        <div v-for="spot in recommendedSpots" :key="`rec-${spot.id}`" class="rec-item">
          <div class="min-w-0">
            <p class="font-semibold text-sm text-gray-800 truncate">{{ spot.name }}</p>
            <p class="text-xs text-gray-500">{{ spot.city }} · {{ spot.type }} · {{ spot.rating || 'N/A' }} 分</p>
          </div>
          <div class="rec-actions">
            <button @click="store.setStartSpot(spot)">起</button>
            <button @click="store.addViaSpot(spot)">经</button>
            <button @click="store.setEndSpot(spot)">终</button>
          </div>
        </div>
      </div>
      <p v-else class="text-xs text-gray-500">输入城市后展示推荐景点。</p>
    </div>

    <div v-if="store.hasRoute" class="bg-blue-50/70 rounded-2xl p-4 ring-1 ring-blue-100">
      <div class="flex items-center justify-between gap-2 mb-2">
        <h4 class="text-sm font-bold text-bupt-blue">路线结果</h4>
        <span v-if="store.isDemoRouteFallback" class="fallback-badge">演示估算</span>
      </div>
      <div class="text-sm text-gray-700 space-y-1">
        <p>城市：{{ store.routeCity || store.startSpot?.city || '-' }}</p>
        <p>交通方式：{{ store.routeTransport === 'bike' ? '骑行' : '步行' }}</p>
        <p>总距离：{{ formatDistance(store.totalDistanceM) }}</p>
        <p>预计耗时：{{ formatDuration(store.estimatedDurationS) }}</p>
        <p>路线：{{ store.routeWaypoints.map((spot) => spot.name).join(' → ') }}</p>
      </div>
      <ol class="segment-list">
        <li v-for="(segment, index) in store.routeSegments" :key="`${segment.from.id}-${segment.to.id}-${index}`">
          {{ index + 1 }}. {{ segment.from.name }} → {{ segment.to.name }} · {{ formatDistance(segment.distanceM) }}
          <span v-if="segment.fallback"> · 演示估算</span>
        </li>
      </ol>
    </div>

    <div v-if="store.selectedSpot" class="bg-emerald-50/70 rounded-2xl p-4 ring-1 ring-emerald-100">
      <h4 class="text-sm font-bold text-emerald-700 mb-1">{{ store.selectedSpot.name }}</h4>
      <p class="text-xs text-gray-600 mb-2">{{ store.selectedSpot.city }} · {{ store.selectedSpot.type }}</p>
      <p class="text-xs text-gray-600 mb-3">{{ store.selectedSpot.description || '暂无描述' }}</p>
      <div class="grid grid-cols-3 gap-2 mb-2">
        <button class="spot-action" @click="store.setStartSpot(store.selectedSpot)">起点</button>
        <button class="spot-action" @click="store.addViaSpot(store.selectedSpot)">途径</button>
        <button class="spot-action" @click="store.setEndSpot(store.selectedSpot)">终点</button>
      </div>
      <button class="w-full px-2 py-1.5 text-xs rounded-md bg-blue-100 text-bupt-blue font-semibold" @click="$emit('view-diaries')">查看社区日记</button>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useNationalMapStore } from '../stores/nationalMap'

defineEmits(['view-diaries'])

const store = useNationalMapStore()
const transport = ref('walk')
const viaSelectId = ref('')
const recommendCity = ref('北京')

const sortedSpots = computed(() => {
  return [...store.spots].sort((a, b) => {
    const cityComp = String(a.city || '').localeCompare(String(b.city || ''), 'zh-Hans-CN')
    if (cityComp !== 0) return cityComp
    return String(a.name || '').localeCompare(String(b.name || ''), 'zh-Hans-CN')
  })
})

const constraintCity = computed(() => store.startSpot?.city || store.endSpot?.city || store.viaSpots[0]?.city || '')

const scopedOptions = computed(() => {
  if (!constraintCity.value) return sortedSpots.value
  return sortedSpots.value.filter((spot) => spot.city === constraintCity.value)
})

const startOptions = computed(() => sortedSpots.value)
const endOptions = computed(() => scopedOptions.value.filter((spot) => spot.id !== store.startSpot?.id))
const viaOptions = computed(() => scopedOptions.value.filter((spot) => {
  if (spot.id === store.startSpot?.id || spot.id === store.endSpot?.id) return false
  return !store.viaSpots.some((via) => via.id === spot.id)
}))

const recommendedSpots = computed(() => {
  const city = recommendCity.value.trim()
  if (!city) return []
  return store.spots
    .filter((spot) => String(spot.city || '').includes(city))
    .sort((a, b) => (b.rating || 0) - (a.rating || 0) || (b.diary_count || 0) - (a.diary_count || 0))
    .slice(0, 6)
})

onMounted(async () => {
  try {
    await store.initialize()
  } catch (error) {
    console.error('Failed to initialize national navigation panel:', error)
  }
})

function handleStartChange(event) {
  const spotId = event.target.value
  store.setStartSpot(spotId ? store.getSpotById(spotId) : null)
}

function handleEndChange(event) {
  const spotId = event.target.value
  store.setEndSpot(spotId ? store.getSpotById(spotId) : null)
}

function handleAddVia() {
  if (!viaSelectId.value) return
  store.addViaSpotById(viaSelectId.value)
  viaSelectId.value = ''
}

async function handleNavigate() {
  try {
    await store.navigateMultiStop(transport.value)
  } catch (error) {
    console.error('OSM navigation failed:', error)
  }
}

function handleReset() {
  transport.value = 'walk'
  viaSelectId.value = ''
  store.resetSelections()
}

async function handleReload() {
  try {
    await store.initialize(true)
  } catch (error) {
    console.error('Failed to reload national map config:', error)
  }
}

function applyCityFilter() {
  if (recommendedSpots.value[0]) {
    store.setSelectedSpot(recommendedSpots.value[0])
  }
}

function formatDistance(meters) {
  if (!meters || meters <= 0) return '0 m'
  if (meters >= 1000) return `${(meters / 1000).toFixed(2)} km`
  return `${meters.toFixed(0)} m`
}

function formatDuration(seconds) {
  if (!seconds || seconds <= 0) return '0 分钟'
  const mins = Math.round(seconds / 60)
  if (mins < 60) return `${mins} 分钟`
  const h = Math.floor(mins / 60)
  const m = mins % 60
  return `${h} 小时 ${m} 分钟`
}
</script>

<style scoped>
.select {
  width: 100%;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  background: rgba(255, 255, 255, 0.82);
  padding: 8px 10px;
  font-size: 13px;
}

.primary-btn,
.small-btn {
  background: #003d74;
  color: #fff;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 700;
}

.reset-btn {
  background: #f1f5f9;
  color: #334155;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 700;
}

.text-bupt-blue {
  color: #003d74;
}

.via-list {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.via-item,
.rec-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.75);
  border: 1px solid rgba(148, 163, 184, 0.25);
  padding: 8px;
  font-size: 12px;
}

.icon-btn,
.rec-actions button,
.spot-action {
  min-width: 28px;
  padding: 5px 7px;
  border-radius: 6px;
  background: #e0f2fe;
  color: #075985;
  font-size: 12px;
}

.rec-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}

.fallback-badge {
  border-radius: 999px;
  background: #ffedd5;
  color: #c2410c;
  padding: 3px 8px;
  font-size: 11px;
  font-weight: 700;
}

.segment-list {
  margin: 10px 0 0;
  padding-left: 18px;
  color: #475569;
  font-size: 12px;
  line-height: 1.7;
}
</style>
