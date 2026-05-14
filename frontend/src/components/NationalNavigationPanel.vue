<template>
  <div class="space-y-4">
    <div class="bg-gradient-to-br from-white/80 to-white/60 backdrop-blur-sm rounded-2xl p-5 ring-1 ring-black/5 shadow-lg">
      <div class="flex items-center justify-between mb-3">
        <h3 class="text-sm font-bold text-gray-800">校外导航（OSM）</h3>
        <button class="text-xs text-bupt-blue font-semibold" @click="handleReload">刷新配置</button>
      </div>

      <div v-if="store.modeLoading || store.spotsLoading" class="text-sm text-gray-600">
        正在加载校外地图配置...
      </div>

      <div v-else-if="store.modeError" class="text-sm text-red-600">
        地图配置加载失败：{{ store.modeError }}
      </div>

      <div v-else-if="store.modeConfig && !store.supportsSlippyMap" class="text-sm text-amber-600">
        后端返回未启用 slippy map，暂不可用。
      </div>

      <div v-else-if="store.spotsError" class="text-sm text-red-600">
        全国景点加载失败：{{ store.spotsError }}
      </div>

      <div v-else-if="!store.hasSpots" class="text-sm text-gray-500">
        暂无全国景点数据。
      </div>

      <template v-else>
        <div class="space-y-3">
          <div>
            <label class="block text-xs font-semibold text-gray-600 mb-1">起点景点</label>
            <select
              :value="store.startSpot?.id || ''"
              class="w-full px-3 py-2 rounded-lg border border-gray-200 bg-white/80 text-sm"
              @change="handleStartChange"
            >
              <option value="">请选择起点</option>
              <option v-for="spot in startOptions" :key="spot.id" :value="spot.id">
                {{ spot.name }}（{{ spot.city }}）
              </option>
            </select>
          </div>

          <div>
            <label class="block text-xs font-semibold text-gray-600 mb-1">终点景点</label>
            <select
              :value="store.endSpot?.id || ''"
              class="w-full px-3 py-2 rounded-lg border border-gray-200 bg-white/80 text-sm"
              @change="handleEndChange"
            >
              <option value="">请选择终点</option>
              <option v-for="spot in endOptions" :key="`end-${spot.id}`" :value="spot.id">
                {{ spot.name }}（{{ spot.city }}）
              </option>
            </select>
          </div>

          <p class="text-xs text-gray-500">
            仅支持同城导航
            <span v-if="constraintCity">（当前城市：{{ constraintCity }}）</span>
          </p>
          <p
            v-if="store.startSpot && store.endSpot && !store.sameCitySelected"
            class="text-xs text-amber-600"
          >
            当前起终点不在同一城市，点击“开始校外导航”会提示不可规划。
          </p>

          <div>
            <label class="block text-xs font-semibold text-gray-600 mb-1">交通方式</label>
            <select
              v-model="transport"
              class="w-full px-3 py-2 rounded-lg border border-gray-200 bg-white/80 text-sm"
            >
              <option value="walk">🚶 步行</option>
              <option value="bike">🚲 骑行</option>
            </select>
          </div>

          <div class="grid grid-cols-2 gap-2 pt-1">
            <button
              class="px-3 py-2 rounded-lg bg-bupt-blue text-white text-sm font-semibold disabled:opacity-50"
              :disabled="!store.canNavigate || store.routeLoading"
              :title="!store.canNavigate ? store.canNavigateHint : (!store.sameCitySelected ? '当前仅支持同城导航' : '')"
              @click="handleNavigate"
            >
              {{ store.routeLoading ? '规划中...' : '开始校外导航' }}
            </button>
            <button
              class="px-3 py-2 rounded-lg bg-gray-100 text-gray-700 text-sm font-semibold"
              @click="handleReset"
            >
              重置
            </button>
          </div>

          <div v-if="store.routeError" class="text-xs text-red-600 pt-1">
            导航失败：{{ store.routeError }}
          </div>
        </div>
      </template>
    </div>

    <div v-if="store.hasRoute" class="bg-blue-50/70 rounded-2xl p-4 ring-1 ring-blue-100">
      <h4 class="text-sm font-bold text-bupt-blue mb-2">路线结果</h4>
      <div class="text-sm text-gray-700 space-y-1">
        <p>城市：{{ store.routeCity || store.startSpot?.city || '-' }}</p>
        <p>交通方式：{{ store.routeTransport === 'bike' ? '骑行' : '步行' }}</p>
        <p>总距离：{{ formatDistance(store.totalDistanceM) }}</p>
        <p>预计耗时：{{ formatDuration(store.estimatedDurationS) }}</p>
        <p>路段数：{{ store.segmentCount }}</p>
        <p>节点数：{{ store.nodeIds.length }}</p>
      </div>
    </div>

    <div v-if="store.selectedSpot" class="bg-emerald-50/70 rounded-2xl p-4 ring-1 ring-emerald-100">
      <h4 class="text-sm font-bold text-emerald-700 mb-1">{{ store.selectedSpot.name }}</h4>
      <p class="text-xs text-gray-600 mb-2">{{ store.selectedSpot.city }} · {{ store.selectedSpot.type }}</p>
      <p class="text-xs text-gray-600 mb-3">{{ store.selectedSpot.description || '暂无描述' }}</p>
      <div class="grid grid-cols-2 gap-2 mb-2">
        <button class="px-2 py-1.5 text-xs rounded-md bg-emerald-100 text-emerald-700" @click="store.setStartSpot(store.selectedSpot)">
          设为起点
        </button>
        <button class="px-2 py-1.5 text-xs rounded-md bg-emerald-100 text-emerald-700" @click="store.setEndSpot(store.selectedSpot)">
          设为终点
        </button>
      </div>
      <button
        class="w-full px-2 py-1.5 text-xs rounded-md bg-blue-100 text-bupt-blue font-semibold"
        @click="$emit('view-diaries')"
      >
        查看社区日记
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'
import { useNationalMapStore } from '../stores/nationalMap'

defineEmits(['view-diaries'])

const store = useNationalMapStore()
const transport = ref('walk')

function toFiniteNumber(value, fallback = 0) {
  const num = Number(value)
  return Number.isFinite(num) ? num : fallback
}

function normalizeCoords(coords) {
  if (!Array.isArray(coords)) return []
  return coords
    .map((coord) => {
      if (!Array.isArray(coord) || coord.length < 2) return null
      const lat = toFiniteNumber(coord[0], NaN)
      const lng = toFiniteNumber(coord[1], NaN)
      if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null
      return [lat, lng]
    })
    .filter(Boolean)
}

function normalizeNumberArray(values) {
  if (!Array.isArray(values)) return []
  return values
    .map((value) => toFiniteNumber(value, NaN))
    .filter((value) => Number.isFinite(value))
}

function normalizeNodeIds(values) {
  if (!Array.isArray(values)) return []
  return values
    .map((value) => Number(value))
    .filter((value) => Number.isInteger(value))
}

async function navigateOsmFallback(transportMode) {
  if (!store.canNavigate) {
    store.routeError = store.canNavigateHint
    return null
  }
  if (!store.sameCitySelected) {
    store.routeError = '当前仅支持同城导航，请选择同一城市的景点'
    return null
  }
  if (store.routeLoading) {
    return null
  }

  const startSpotId = store.startSpot?.id
  const endSpotId = store.endSpot?.id
  if (!startSpotId || !endSpotId) {
    store.routeError = '请选择起点和终点'
    return null
  }

  const resolvedTransport = transportMode === 'bike' ? 'bike' : 'walk'
  store.routeLoading = true
  store.routeError = null

  try {
    const result = await api.navigateOsm({
      start_spot_id: startSpotId,
      end_spot_id: endSpotId,
      transport: resolvedTransport,
    })
    const segmentDistancesM = normalizeNumberArray(result?.segment_distances_m)
    const segmentCount = Math.max(0, Math.round(toFiniteNumber(result?.segment_count, segmentDistancesM.length)))

    store.routeCoords = normalizeCoords(result?.path_coords)
    store.nodeIds = normalizeNodeIds(result?.node_ids)
    store.totalDistanceM = toFiniteNumber(result?.total_distance_m, 0)
    store.segmentCount = segmentCount
    store.segmentDistancesM = segmentDistancesM
    store.estimatedDurationS = toFiniteNumber(result?.estimated_duration_s, 0)
    store.routeCity = typeof result?.city === 'string' ? result.city : (store.startSpot?.city || '')
    store.routeTransport =
      result?.transport === 'bike' || result?.transport === 'walk'
        ? result.transport
        : resolvedTransport
    return result
  } catch (error) {
    store.routeError = error?.message || '导航请求失败'
    throw error
  } finally {
    store.routeLoading = false
  }
}

const sortedSpots = computed(() => {
  return [...store.spots].sort((a, b) => {
    const cityComp = a.city.localeCompare(b.city, 'zh-Hans-CN')
    if (cityComp !== 0) return cityComp
    return a.name.localeCompare(b.name, 'zh-Hans-CN')
  })
})

const constraintCity = computed(() => store.startSpot?.city || store.endSpot?.city || '')

const startOptions = computed(() => {
  if (!store.endSpot?.city) return sortedSpots.value
  return sortedSpots.value.filter((spot) => spot.city === store.endSpot.city || spot.id === store.startSpot?.id)
})

const endOptions = computed(() => {
  if (!store.startSpot?.city) return sortedSpots.value
  return sortedSpots.value.filter((spot) => spot.city === store.startSpot.city || spot.id === store.endSpot?.id)
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
  if (!spotId) {
    store.setStartSpot(null)
    return
  }
  store.setStartSpotById(spotId)
}

function handleEndChange(event) {
  const spotId = event.target.value
  if (!spotId) {
    store.setEndSpot(null)
    return
  }
  store.setEndSpotById(spotId)
}

async function handleNavigate() {
  try {
    const navigate =
      typeof store.navigateOsm === 'function'
        ? store.navigateOsm.bind(store)
        : navigateOsmFallback
    await navigate(transport.value)
  } catch (error) {
    console.error('OSM navigation failed:', error)
  }
}

function handleReset() {
  transport.value = 'walk'
  store.resetSelections()
}

async function handleReload() {
  try {
    await store.initialize(true)
  } catch (error) {
    console.error('Failed to reload national map config:', error)
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
.bg-bupt-blue {
  background-color: #003d74;
}

.text-bupt-blue {
  color: #003d74;
}
</style>
