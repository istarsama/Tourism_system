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

function isSameCity(start, end) {
  if (!start || !end) return true
  return start.city === end.city
}

function haversineMeters(a, b) {
  const r = 6371000
  const lat1 = Number(a.latitude) * Math.PI / 180
  const lat2 = Number(b.latitude) * Math.PI / 180
  const dLat = (Number(b.latitude) - Number(a.latitude)) * Math.PI / 180
  const dLng = (Number(b.longitude) - Number(a.longitude)) * Math.PI / 180
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) ** 2
  return 2 * r * Math.atan2(Math.sqrt(h), Math.sqrt(1 - h))
}

function buildDemoSegment(start, end, transport) {
  const distance = haversineMeters(start, end)
  const speed = transport === 'bike' ? 4.2 : 1.25
  const steps = 16
  const coords = []
  for (let i = 0; i <= steps; i += 1) {
    const t = i / steps
    coords.push([
      Number(start.latitude) + (Number(end.latitude) - Number(start.latitude)) * t,
      Number(start.longitude) + (Number(end.longitude) - Number(start.longitude)) * t,
    ])
  }
  return {
    city: start.city,
    transport,
    nodeIds: [],
    pathCoords: coords,
    totalDistanceM: distance,
    segmentCount: 1,
    segmentDistancesM: [distance],
    estimatedDurationS: distance / speed,
    raw: null,
    fallback: true,
  }
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
  const viaSpots = ref([])

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
  const routeSegments = ref([])
  const routeWaypoints = ref([])
  const isDemoRouteFallback = ref(false)
  const activeRouteRequestId = ref(0)

  const isInitializing = ref(false)

  const waypointSpots = computed(() => [startSpot.value, ...viaSpots.value, endSpot.value].filter(Boolean))
  const sameCitySelected = computed(() => waypointSpots.value.every((spot) => isSameCity(waypointSpots.value[0], spot)))
  const canNavigate = computed(() => {
    if (!startSpot.value || !endSpot.value) return false
    if (startSpot.value.id === endSpot.value.id) return false
    return true
  })
  const canNavigateHint = computed(() => {
    if (!startSpot.value || !endSpot.value) return '请选择起点和终点'
    if (startSpot.value.id === endSpot.value.id) return '起点和终点不能相同'
    if (!sameCitySelected.value) return '起点、途径点和终点需在同一城市'
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
    routeSegments.value = []
    routeWaypoints.value = []
    isDemoRouteFallback.value = false
  }

  function removeViaId(spotId) {
    viaSpots.value = viaSpots.value.filter((spot) => spot.id !== spotId)
  }

  function setStartSpot(spot) {
    startSpot.value = spot || null
    if (startSpot.value) {
      if (endSpot.value?.id === startSpot.value.id) endSpot.value = null
      removeViaId(startSpot.value.id)
    }
    resetRoute()
  }

  function setEndSpot(spot) {
    endSpot.value = spot || null
    if (endSpot.value) {
      if (startSpot.value?.id === endSpot.value.id) startSpot.value = null
      removeViaId(endSpot.value.id)
    }
    resetRoute()
  }

  function setStartSpotById(spotId) {
    setStartSpot(getSpotById(spotId))
  }

  function setEndSpotById(spotId) {
    setEndSpot(getSpotById(spotId))
  }

  function addViaSpot(spot) {
    if (!spot) return
    if (startSpot.value?.id === spot.id || endSpot.value?.id === spot.id) return
    if (viaSpots.value.some((item) => item.id === spot.id)) return
    viaSpots.value.push(spot)
    resetRoute()
  }

  function addViaSpotById(spotId) {
    addViaSpot(getSpotById(spotId))
  }

  function removeViaSpot(spotId) {
    removeViaId(Number(spotId))
    resetRoute()
  }

  function moveViaSpot(index, direction) {
    const nextIndex = index + direction
    if (nextIndex < 0 || nextIndex >= viaSpots.value.length) return
    const copy = [...viaSpots.value]
    const [item] = copy.splice(index, 1)
    copy.splice(nextIndex, 0, item)
    viaSpots.value = copy
    resetRoute()
  }

  function resetSelections() {
    selectedSpot.value = null
    startSpot.value = null
    endSpot.value = null
    viaSpots.value = []
    resetRoute()
  }

  async function planSegment(start, end, transport) {
    try {
      const result = await api.navigateOsm({
        start_spot_id: start.id,
        end_spot_id: end.id,
        transport,
      })
      return { ...normalizeRouteResult(result, transport), fallback: false }
    } catch (error) {
      console.warn('OSM segment failed, using demo fallback:', error)
      return buildDemoSegment(start, end, transport)
    }
  }

  async function navigateMultiStop(transport = DEFAULT_TRANSPORT) {
    if (!canNavigate.value) {
      routeError.value = canNavigateHint.value
      return null
    }
    if (!sameCitySelected.value) {
      routeError.value = '起点、途径点和终点需在同一城市，当前仅支持同城串联规划'
      return null
    }
    if (routeLoading.value) return null

    const requestId = activeRouteRequestId.value + 1
    activeRouteRequestId.value = requestId
    routeLoading.value = true
    routeError.value = null

    try {
      const waypoints = [startSpot.value, ...viaSpots.value, endSpot.value]
      const mergedCoords = []
      const mergedNodeIds = []
      const mergedDistances = []
      const segments = []
      let totalDistance = 0
      let totalDuration = 0
      let totalSegments = 0
      let usedFallback = false

      for (let i = 1; i < waypoints.length; i += 1) {
        const from = waypoints[i - 1]
        const to = waypoints[i]
        const segment = await planSegment(from, to, transport)
        if (requestId !== activeRouteRequestId.value) return null

        const coords = segment.pathCoords
        if (coords.length) {
          mergedCoords.push(...(mergedCoords.length ? coords.slice(1) : coords))
        }
        mergedNodeIds.push(...segment.nodeIds)
        mergedDistances.push(...segment.segmentDistancesM)
        totalDistance += segment.totalDistanceM
        totalDuration += segment.estimatedDurationS
        totalSegments += Math.max(1, segment.segmentCount)
        usedFallback = usedFallback || segment.fallback
        segments.push({
          from,
          to,
          distanceM: segment.totalDistanceM,
          durationS: segment.estimatedDurationS,
          fallback: segment.fallback,
        })
      }

      routeCoords.value = mergedCoords
      nodeIds.value = mergedNodeIds
      totalDistanceM.value = totalDistance
      segmentCount.value = totalSegments
      segmentDistancesM.value = mergedDistances
      estimatedDurationS.value = totalDuration
      routeCity.value = startSpot.value?.city || ''
      routeTransport.value = transport === 'bike' ? 'bike' : 'walk'
      routeSegments.value = segments
      routeWaypoints.value = waypoints
      isDemoRouteFallback.value = usedFallback
      return { segments, path_coords: mergedCoords, fallback: usedFallback }
    } catch (err) {
      if (requestId === activeRouteRequestId.value) {
        routeError.value = err.message || '路线规划失败'
      }
      throw err
    } finally {
      if (requestId === activeRouteRequestId.value) routeLoading.value = false
    }
  }

  async function navigateOsm(transport = DEFAULT_TRANSPORT) {
    return navigateMultiStop(transport)
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
    viaSpots,
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
    routeSegments,
    routeWaypoints,
    isDemoRouteFallback,
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
    navigateMultiStop,
    setSelectedSpot,
    setStartSpot,
    setEndSpot,
    setStartSpotById,
    setEndSpotById,
    addViaSpot,
    addViaSpotById,
    removeViaSpot,
    moveViaSpot,
    getSpotById,
    resetRoute,
    resetSelections,
  }
})
