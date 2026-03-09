<template>
  <div class="national-map-container">
    <div ref="mapRef" class="map-surface"></div>

    <div v-if="showLoading" class="status-overlay">
      <p>正在加载校外地图...</p>
    </div>

    <div v-else-if="store.modeError" class="status-overlay">
      <p>地图配置加载失败：{{ store.modeError }}</p>
      <button class="retry-btn" @click="retryLoad">重试</button>
    </div>

    <div v-else-if="store.modeConfig && !store.supportsSlippyMap" class="status-overlay">
      <p>当前后端配置未启用 OSM slippy map（supports_slippy_map=false）。</p>
    </div>

    <div v-else-if="store.spotsError" class="status-overlay">
      <p>全国景点数据加载失败：{{ store.spotsError }}</p>
      <button class="retry-btn" @click="retryLoad">重试</button>
    </div>

    <div v-else-if="!store.hasSpots" class="status-overlay">
      <p>暂无可用的全国景点数据。</p>
    </div>
  </div>
</template>

<script setup>
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import L from 'leaflet'
import { useNationalMapStore } from '../stores/nationalMap'

const store = useNationalMapStore()
const mapRef = ref(null)
const showLoading = ref(true)

let mapInstance = null
let tileLayer = null
let markerLayer = null
let routeLayer = null
let hasAutoFitted = false

onMounted(async () => {
  await initNationalMap()
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  if (mapInstance) {
    mapInstance.remove()
    mapInstance = null
  }
})

watch(
  () => store.modeConfig,
  () => {
    ensureMapReady()
  },
  { deep: true }
)

watch(
  () => [store.spots, store.startSpot, store.endSpot, store.selectedSpot],
  () => {
    renderMarkers()
  },
  { deep: true }
)

watch(
  () => store.routeCoords,
  () => {
    renderRoute()
  },
  { deep: true }
)

async function initNationalMap(force = false) {
  showLoading.value = true
  try {
    await store.initialize(force)
  } catch (error) {
    console.error('Failed to initialize national map:', error)
  } finally {
    await nextTick()
    ensureMapReady()
    renderMarkers()
    renderRoute()
    queueMapResize()
    showLoading.value = false
  }
}

function ensureMapReady() {
  if (mapInstance || !mapRef.value || !store.modeConfig || !store.supportsSlippyMap) {
    return
  }

  const centerLat = store.modeConfig.center_lat ?? 35.8617
  const centerLng = store.modeConfig.center_lng ?? 104.1954
  const zoomLevel = store.modeConfig.zoom_level ?? 5

  mapInstance = L.map(mapRef.value, {
    zoomControl: true,
  }).setView([centerLat, centerLng], zoomLevel)

  const tileConfig = store.modeConfig.tile_layer || {}
  tileLayer = L.tileLayer(tileConfig.tile_url || 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: tileConfig.attribution || '&copy; OpenStreetMap contributors',
    minZoom: tileConfig.min_zoom ?? 3,
    maxZoom: tileConfig.max_zoom ?? 19,
    subdomains: tileConfig.subdomains?.length ? tileConfig.subdomains : undefined,
  })
  tileLayer.addTo(mapInstance)
  window.addEventListener('resize', handleResize)
  queueMapResize()
}

function getMarkerStyle(spot) {
  if (store.startSpot?.id === spot.id) {
    return { color: '#059669', fillColor: '#10b981' }
  }
  if (store.endSpot?.id === spot.id) {
    return { color: '#dc2626', fillColor: '#ef4444' }
  }
  if (store.selectedSpot?.id === spot.id) {
    return { color: '#d97706', fillColor: '#f59e0b' }
  }
  return { color: '#1d4ed8', fillColor: '#3b82f6' }
}

function handleMarkerClick(spot) {
  store.setSelectedSpot(spot)

  if (store.startSpot?.id === spot.id) {
    store.setStartSpot(null)
  } else if (store.endSpot?.id === spot.id) {
    store.setEndSpot(null)
  } else if (!store.startSpot) {
    store.setStartSpot(spot)
  } else if (!store.endSpot) {
    store.setEndSpot(spot)
  } else {
    store.setEndSpot(spot)
  }
}

function renderMarkers() {
  if (!mapInstance || !store.supportsSlippyMap) return

  if (markerLayer) {
    mapInstance.removeLayer(markerLayer)
  }
  markerLayer = L.layerGroup()

  for (const spot of store.spots) {
    const markerStyle = getMarkerStyle(spot)
    const marker = L.circleMarker([spot.latitude, spot.longitude], {
      radius: 7,
      color: markerStyle.color,
      fillColor: markerStyle.fillColor,
      fillOpacity: 0.9,
      weight: 2,
    })

    marker.bindTooltip(`${spot.name}（${spot.city}）`)
    marker.on('click', () => handleMarkerClick(spot))
    markerLayer.addLayer(marker)
  }

  markerLayer.addTo(mapInstance)

  if (!hasAutoFitted && store.spots.length > 0 && !store.hasRoute) {
    const bounds = L.latLngBounds(store.spots.map((spot) => [spot.latitude, spot.longitude]))
    mapInstance.fitBounds(bounds, { padding: [20, 20], maxZoom: 7 })
    hasAutoFitted = true
  }
}

function renderRoute() {
  if (!mapInstance) return

  if (routeLayer) {
    mapInstance.removeLayer(routeLayer)
    routeLayer = null
  }

  if (!store.hasRoute) return

  routeLayer = L.polyline(store.routeCoords, {
    color: '#f97316',
    weight: 5,
    opacity: 0.9,
  }).addTo(mapInstance)

  mapInstance.fitBounds(routeLayer.getBounds(), { padding: [30, 30] })
}

async function retryLoad() {
  await initNationalMap(true)
}

function handleResize() {
  queueMapResize()
}

function queueMapResize() {
  if (!mapInstance) return
  setTimeout(() => {
    mapInstance?.invalidateSize()
  }, 0)
}
</script>

<style scoped>
.national-map-container {
  position: absolute;
  inset: 0;
  z-index: 0;
  min-height: 320px;
  background: #e5e7eb;
}

.map-surface {
  width: 100%;
  height: 100%;
  min-height: inherit;
}

.status-overlay {
  position: absolute;
  inset: 0;
  background: rgba(255, 255, 255, 0.9);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 12px;
  color: #1f2937;
  text-align: center;
  padding: 20px;
  z-index: 500;
}

.retry-btn {
  border: none;
  border-radius: 8px;
  background: #003d74;
  color: #fff;
  padding: 8px 14px;
  cursor: pointer;
}
</style>
