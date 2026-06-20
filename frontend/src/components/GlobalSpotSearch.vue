<template>
  <div class="bg-gradient-to-br from-white/80 to-white/60 backdrop-blur-sm rounded-2xl p-4 ring-1 ring-black/5 shadow-lg mb-3">
    <div class="flex items-center justify-between mb-3">
      <h3 class="text-sm font-bold text-gray-800">景点搜索</h3>
      <span class="text-xs text-gray-500">{{ scopeLabel }}</span>
    </div>

    <SearchInput
      v-model="query"
      :placeholder="placeholder"
      :selected="selectedItem"
      :search-fn="searchCurrentScope"
      @select="handleSelect"
    />

    <div v-if="selectedItem" class="mt-3 rounded-xl bg-white/70 p-3 ring-1 ring-black/5">
      <div class="flex items-start justify-between gap-2 mb-2">
        <div class="min-w-0">
          <h4 class="text-sm font-bold text-bupt-blue truncate">{{ selectedItem.name }}</h4>
          <p class="text-xs text-gray-500 truncate">{{ selectedMeta }}</p>
        </div>
        <button class="text-xs text-gray-500 px-2 py-1" @click="clearSelection">清除</button>
      </div>

      <p v-if="selectedDescription" class="text-xs text-gray-600 leading-5 mb-3">{{ selectedDescription }}</p>

      <div class="grid grid-cols-2 gap-2">
        <button class="action-btn" @click="setAsStart">设为起点</button>
        <button class="action-btn" @click="setAsEnd">设为终点</button>
        <button
          v-if="mapStore.activeScope === 'national'"
          class="action-btn col-span-2"
          @click="nationalStore.addViaSpot(selectedItem)"
        >
          添加为途径景点
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import SearchInput from './SearchInput.vue'
import { api } from '../api'
import { useMapStore } from '../stores/map'
import { useIndoorMapStore } from '../stores/indoorMap'
import { useNationalMapStore } from '../stores/nationalMap'

const mapStore = useMapStore()
const indoorStore = useIndoorMapStore()
const nationalStore = useNationalMapStore()

const query = ref('')
const selectedItem = ref(null)

const scopeLabel = computed(() => {
  if (mapStore.activeScope === 'indoor') return '教学楼室内'
  if (mapStore.activeScope === 'national') return '全国景点'
  return '校园景点'
})

const placeholder = computed(() => {
  if (mapStore.activeScope === 'indoor') return '搜索厕所、楼梯、自动售卖机...'
  if (mapStore.activeScope === 'national') return '搜索故宫、西湖、外滩...'
  return '搜索图书馆、食堂、教学楼...'
})

const selectedMeta = computed(() => {
  if (!selectedItem.value) return ''
  if (mapStore.activeScope === 'national') return `${selectedItem.value.city || '-'} · ${selectedItem.value.type || '景点'}`
  if (mapStore.activeScope === 'indoor') return selectedItem.value.type || '室内地标'
  return '校园景点'
})

const selectedDescription = computed(() => selectedItem.value?.description || selectedItem.value?.detail || selectedItem.value?.desc || '')

async function searchCurrentScope(value) {
  if (mapStore.activeScope === 'indoor') {
    return indoorStore.searchLandmarks(value, 8)
  }
  if (mapStore.activeScope === 'national') {
    try {
      return await api.searchSpots(value, 8, 'national')
    } catch (error) {
      const q = value.trim().toLowerCase()
      return nationalStore.spots
        .filter((spot) => `${spot.name} ${spot.city} ${spot.type}`.toLowerCase().includes(q))
        .slice(0, 8)
        .map((spot) => ({ ...spot, score: 82, scope: 'national' }))
    }
  }
  return mapStore.searchSpots(value)
}

function handleSelect(item) {
  selectedItem.value = item
  query.value = item?.name || ''
  if (!item) return

  if (mapStore.activeScope === 'indoor') {
    indoorStore.setSelectedNode(item)
    return
  }
  if (mapStore.activeScope === 'national') {
    const fullSpot = nationalStore.getSpotById?.(item.id) || item
    selectedItem.value = fullSpot
    nationalStore.setSelectedSpot(fullSpot)
    return
  }
  mapStore.selectNode(item)
}

function clearSelection() {
  selectedItem.value = null
  query.value = ''
  if (mapStore.activeScope === 'indoor') indoorStore.setSelectedNode(null)
  if (mapStore.activeScope === 'national') nationalStore.setSelectedSpot(null)
  if (mapStore.activeScope === 'campus') mapStore.clearSelectedSpot()
}

function setAsStart() {
  if (!selectedItem.value) return
  if (mapStore.activeScope === 'indoor') indoorStore.setStartNode(selectedItem.value)
  else if (mapStore.activeScope === 'national') nationalStore.setStartSpot(selectedItem.value)
  else mapStore.setStart(selectedItem.value)
}

function setAsEnd() {
  if (!selectedItem.value) return
  if (mapStore.activeScope === 'indoor') indoorStore.setEndNode(selectedItem.value)
  else if (mapStore.activeScope === 'national') nationalStore.setEndSpot(selectedItem.value)
  else mapStore.setEnd(selectedItem.value)
}
</script>

<style scoped>
.text-bupt-blue {
  color: #003d74;
}

.action-btn {
  border-radius: 8px;
  background: #e0f2fe;
  color: #075985;
  padding: 7px 9px;
  font-size: 12px;
  font-weight: 700;
}

.action-btn:hover {
  background: #dbeafe;
  color: #003d74;
}
</style>
