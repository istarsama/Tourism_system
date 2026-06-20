import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api } from '../api'

const DEFAULT_TRANSPORT = 'walk'

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

function normalizeRouteResult(result, fallbackTransport = DEFAULT_TRANSPORT) {
  const segmentDistancesM = normalizeNumberArray(result?.segment_distances_m)
  const segmentCount = Math.max(
    0,
    Math.round(toFiniteNumber(result?.segment_count, segmentDistancesM.length))
  )
  const transport =
    result?.transport === 'bike' || result?.transport === 'walk'
      ? result.transport
      : fallbackTransport

  return {
    city: typeof result?.city === 'string' ? result.city : '',
    transport,
    nodeIds: normalizeNodeIds(result?.node_ids),
    pathCoords: normalizeCoords(result?.path_coords),
    totalDistanceM: toFiniteNumber(result?.total_distance_m, 0),
    segmentCount,
    segmentDistancesM,
    estimatedDurationS: toFiniteNumber(result?.estimated_duration_s, 0),
    raw: result,
  }
}

function areSameCity(spots) {
  const selectedSpots = spots.filter(Boolean)
  if (selectedSpots.length <= 1) return true
  return selectedSpots.every((spot) => spot.city === selectedSpots[0].city)
}

export const useNationalMapStore = defineStore('nationalMap', () => {
  const modeConfig = ref(null)
  const modeLoading = ref(false)
  const modeError = ref(null)

  const spots = ref([])
  const spotsLoading = ref(false)
  const spotsError = ref(null)

  const selectedSpot = ref(null)
  const startSpot = ref(null)
  const endSpot = ref(null)
  const waypointSpots = ref([])

  const routeCoords = ref([])
  const nodeIds = ref([])
  const totalDistanceM = ref(0)
  const segmentCount = ref(0)
  const segmentDistancesM = ref([])
  const estimatedDurationS = ref(0)
  const routeCity = ref('')
  const routeTransport = ref(DEFAULT_TRANSPORT)
  const routeLoading = ref(false)
  const routeError = ref(null)
  const activeRouteRequestId = ref(0)

  const isInitializing = ref(false)

  const routeSpots = computed(() => [
    startSpot.value,
    ...waypointSpots.value,
    endSpot.value,
  ])
  const sameCitySelected = computed(() => areSameCity(routeSpots.value))
  const canNavigate = computed(() => {
    if (!startSpot.value || !endSpot.value) return false
    if (waypointSpots.value.some((spot) => !spot)) return false
    const ids = routeSpots.value.filter(Boolean).map((spot) => spot.id)
    return ids.length === new Set(ids).size
  })
  const canNavigateHint = computed(() => {
    if (!startSpot.value || !endSpot.value) return '请选择起点和终点'
    if (waypointSpots.value.some((spot) => !spot)) return '请选择全部途经点或删除空途经点'
    const ids = routeSpots.value.filter(Boolean).map((spot) => spot.id)
    if (ids.length !== new Set(ids).size) return '起点、途经点和终点不能重复'
    return ''
  })
  const hasRoute = computed(() => routeCoords.value.length > 1)
  const supportsSlippyMap = computed(() => !!modeConfig.value?.supports_slippy_map)
  const hasSpots = computed(() => spots.value.length > 0)

  async function loadModeConfig() {
    modeLoading.value = true
    modeError.value = null
    try {
      const data = await api.getMapMode('national')
      modeConfig.value = data
      return data
    } catch (err) {
      modeError.value = err.message
      throw err
    } finally {
      modeLoading.value = false
    }
  }

  async function loadNationalSpots(params = {}) {
    spotsLoading.value = true
    spotsError.value = null
    try {
      const data = await api.getNationalSpots({ limit: 300, ...params })
      spots.value = data
      return data
    } catch (err) {
      spotsError.value = err.message
      throw err
    } finally {
      spotsLoading.value = false
    }
  }

  async function initialize(force = false) {
    if (isInitializing.value) return

    isInitializing.value = true
    try {
      if (force || !modeConfig.value) {
        await loadModeConfig()
      }

      if (!supportsSlippyMap.value) {
        return
      }

      if (force || !spots.value.length) {
        await loadNationalSpots()
      }
    } finally {
      isInitializing.value = false
    }
  }

  function setSelectedSpot(spot) {
    selectedSpot.value = spot
  }

  function getSpotById(spotId) {
    const id = Number(spotId)
    return spots.value.find((spot) => spot.id === id) || null
  }

  function resetRoute() {
    activeRouteRequestId.value += 1
    routeCoords.value = []
    nodeIds.value = []
    totalDistanceM.value = 0
    segmentCount.value = 0
    segmentDistancesM.value = []
    estimatedDurationS.value = 0
    routeCity.value = ''
    routeTransport.value = DEFAULT_TRANSPORT
    routeError.value = null
    routeLoading.value = false
  }

  function setStartSpot(spot) {
    startSpot.value = spot || null
    if (startSpot.value && endSpot.value && endSpot.value.id === startSpot.value.id) {
      endSpot.value = null
    }
    if (startSpot.value) {
      waypointSpots.value = waypointSpots.value.filter(
        (waypoint) => !waypoint || waypoint.id !== startSpot.value.id
      )
    }
    resetRoute()
  }

  function setEndSpot(spot) {
    endSpot.value = spot || null
    if (endSpot.value && startSpot.value && startSpot.value.id === endSpot.value.id) {
      startSpot.value = null
    }
    if (endSpot.value) {
      waypointSpots.value = waypointSpots.value.filter(
        (waypoint) => !waypoint || waypoint.id !== endSpot.value.id
      )
    }
    resetRoute()
  }

  function addWaypointSpot(spot = null) {
    if (
      spot &&
      routeSpots.value.filter(Boolean).some((selected) => selected.id === spot.id)
    ) {
      return false
    }
    waypointSpots.value.push(spot || null)
    resetRoute()
    return true
  }

  function setWaypointSpot(index, spot) {
    if (index < 0 || index >= waypointSpots.value.length) return false
    if (
      spot &&
      routeSpots.value
        .filter(Boolean)
        .some((selected, selectedIndex) => {
          const routeIndex = selectedIndex - 1
          return selected.id === spot.id && routeIndex !== index
        })
    ) {
      return false
    }
    waypointSpots.value[index] = spot || null
    resetRoute()
    return true
  }

  function removeWaypointSpot(index) {
    if (index < 0 || index >= waypointSpots.value.length) return
    waypointSpots.value.splice(index, 1)
    resetRoute()
  }

  function setStartSpotById(spotId) {
    setStartSpot(getSpotById(spotId))
  }

  function setEndSpotById(spotId) {
    setEndSpot(getSpotById(spotId))
  }

  function resetSelections() {
    selectedSpot.value = null
    startSpot.value = null
    endSpot.value = null
    waypointSpots.value = []
    resetRoute()
  }

  async function navigateOsm(transport = DEFAULT_TRANSPORT) {
    if (!canNavigate.value) {
      routeError.value = canNavigateHint.value
      return null
    }
    if (!sameCitySelected.value) {
      routeError.value = '当前仅支持同城导航，请选择同一城市的景点'
      return null
    }
    if (routeLoading.value) {
      return null
    }

    const requestId = activeRouteRequestId.value + 1
    activeRouteRequestId.value = requestId

    routeLoading.value = true
    routeError.value = null
    try {
      const result = await api.navigateOsm({
        start_spot_id: startSpot.value.id,
        end_spot_id: endSpot.value.id,
        via_spot_ids: waypointSpots.value.map((spot) => spot.id),
        transport,
      })

      if (requestId !== activeRouteRequestId.value) {
        return null
      }

      const normalized = normalizeRouteResult(result, transport)
      routeCoords.value = normalized.pathCoords
      nodeIds.value = normalized.nodeIds
      totalDistanceM.value = normalized.totalDistanceM
      segmentCount.value = normalized.segmentCount
      segmentDistancesM.value = normalized.segmentDistancesM
      estimatedDurationS.value = normalized.estimatedDurationS
      routeCity.value = normalized.city || startSpot.value?.city || ''
      routeTransport.value = normalized.transport
      return normalized.raw
    } catch (err) {
      if (requestId === activeRouteRequestId.value) {
        routeError.value = err.message
      }
      throw err
    } finally {
      if (requestId === activeRouteRequestId.value) {
        routeLoading.value = false
      }
    }
  }

  return {
    modeConfig,
    modeLoading,
    modeError,
    spots,
    spotsLoading,
    spotsError,
    selectedSpot,
    startSpot,
    endSpot,
    waypointSpots,
    routeCoords,
    nodeIds,
    totalDistanceM,
    segmentCount,
    segmentDistancesM,
    estimatedDurationS,
    routeCity,
    routeTransport,
    routeLoading,
    routeError,
    isInitializing,
    canNavigate,
    canNavigateHint,
    sameCitySelected,
    hasRoute,
    supportsSlippyMap,
    hasSpots,
    initialize,
    loadModeConfig,
    loadNationalSpots,
    navigate: navigateOsm,
    navigateOsm,
    setSelectedSpot,
    setStartSpot,
    setEndSpot,
    addWaypointSpot,
    setWaypointSpot,
    removeWaypointSpot,
    setStartSpotById,
    setEndSpotById,
    resetRoute,
    resetSelections,
  }
})
