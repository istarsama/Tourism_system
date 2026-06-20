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
    legs: Array.isArray(result?.legs)
      ? result.legs.map((leg) => ({
          startSpotId: Number(leg?.start_spot_id),
          endSpotId: Number(leg?.end_spot_id),
          totalDistanceM: toFiniteNumber(leg?.total_distance_m, 0),
          segmentCount: Math.max(0, Math.round(toFiniteNumber(leg?.segment_count, 0))),
          estimatedDurationS: toFiniteNumber(leg?.estimated_duration_s, 0),
        }))
      : [],
    raw: result,
  }
}

function areSameCity(spots) {
  const selectedSpots = spots.filter(Boolean)
  if (selectedSpots.length <= 1) return true
  return selectedSpots.every((spot) => spot.city === selectedSpots[0].city)
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

function buildDemoRoute(waypoints, transport) {
  const segments = []
  const pathCoords = []
  const segmentDistancesM = []
  let totalDistanceM = 0
  let estimatedDurationS = 0

  for (let index = 1; index < waypoints.length; index += 1) {
    const from = waypoints[index - 1]
    const to = waypoints[index]
    const segment = buildDemoSegment(from, to, transport)
    pathCoords.push(...(pathCoords.length ? segment.pathCoords.slice(1) : segment.pathCoords))
    segmentDistancesM.push(segment.totalDistanceM)
    totalDistanceM += segment.totalDistanceM
    estimatedDurationS += segment.estimatedDurationS
    segments.push({
      from,
      to,
      distanceM: segment.totalDistanceM,
      durationS: segment.estimatedDurationS,
      fallback: true,
      estimated: false,
    })
  }

  return {
    city: waypoints[0]?.city || '',
    transport,
    nodeIds: [],
    pathCoords,
    totalDistanceM,
    segmentCount: segments.length,
    segmentDistancesM,
    estimatedDurationS,
    legs: [],
    segments,
    raw: null,
    fallback: true,
  }
}

function buildRouteSegments(waypoints, normalized) {
  const legCount = waypoints.length - 1
  if (normalized.legs.length === legCount) {
    return normalized.legs.map((leg, index) => ({
      from: waypoints[index],
      to: waypoints[index + 1],
      distanceM: leg.totalDistanceM,
      durationS: leg.estimatedDurationS,
      fallback: false,
      estimated: false,
    }))
  }

  const directDistances = waypoints.slice(1).map((to, index) => {
    return haversineMeters(waypoints[index], to)
  })
  const directTotal = directDistances.reduce((sum, distance) => sum + distance, 0)

  return directDistances.map((distance, index) => {
    const ratio = directTotal > 0 ? distance / directTotal : 1 / Math.max(legCount, 1)
    return {
      from: waypoints[index],
      to: waypoints[index + 1],
      distanceM: normalized.totalDistanceM * ratio,
      durationS: normalized.estimatedDurationS * ratio,
      fallback: false,
      estimated: true,
    }
  })
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
  const routeWarning = ref(null)
  const routeSegments = ref([])
  const routeWaypoints = ref([])
  const isDemoRouteFallback = ref(false)
  const activeRouteRequestId = ref(0)
  let activeRouteController = null

  const isInitializing = ref(false)

  const routeSpots = computed(() => [
    startSpot.value,
    ...viaSpots.value,
    endSpot.value,
  ])
  const sameCitySelected = computed(() => areSameCity(routeSpots.value))
  const canNavigate = computed(() => {
    if (!startSpot.value || !endSpot.value) return false
    const ids = routeSpots.value.filter(Boolean).map((spot) => spot.id)
    return ids.length === new Set(ids).size && sameCitySelected.value
  })
  const canNavigateHint = computed(() => {
    if (!startSpot.value || !endSpot.value) return '请选择起点和终点'
    const ids = routeSpots.value.filter(Boolean).map((spot) => spot.id)
    if (ids.length !== new Set(ids).size) return '起点、途经点和终点不能重复'
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
    activeRouteController?.abort()
    activeRouteController = null
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
    routeWarning.value = null
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

  function applyRouteResult(result, waypoints, fallback = false) {
    routeCoords.value = result.pathCoords
    nodeIds.value = result.nodeIds
    totalDistanceM.value = result.totalDistanceM
    segmentCount.value = result.segmentCount
    segmentDistancesM.value = result.segmentDistancesM
    estimatedDurationS.value = result.estimatedDurationS
    routeCity.value = result.city || waypoints[0]?.city || ''
    routeTransport.value = result.transport === 'bike' ? 'bike' : 'walk'
    routeSegments.value = result.segments || buildRouteSegments(waypoints, result)
    routeWaypoints.value = waypoints
    isDemoRouteFallback.value = fallback
  }

  function cancelRoutePlanning() {
    if (!routeLoading.value) return
    activeRouteRequestId.value += 1
    activeRouteController?.abort()
    activeRouteController = null
    routeLoading.value = false
    routeError.value = null
    routeWarning.value = '已取消路线规划'
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
    const controller = new AbortController()
    activeRouteController = controller
    const normalizedTransport = transport === 'bike' ? 'bike' : 'walk'
    const waypoints = [startSpot.value, ...viaSpots.value, endSpot.value]
    routeLoading.value = true
    routeError.value = null
    routeWarning.value = null

    try {
      const result = await api.navigateOsm(
        {
          start_spot_id: waypoints[0].id,
          end_spot_id: waypoints[waypoints.length - 1].id,
          via_spot_ids: waypoints.slice(1, -1).map((spot) => spot.id),
          transport: normalizedTransport,
        },
        { signal: controller.signal }
      )
      if (requestId !== activeRouteRequestId.value) return null

      const normalized = normalizeRouteResult(result, normalizedTransport)
      if (normalized.pathCoords.length < 2) {
        throw new Error('后端未返回有效的路线坐标')
      }
      applyRouteResult(normalized, waypoints)
      return result
    } catch (err) {
      if (requestId !== activeRouteRequestId.value || controller.signal.aborted) return null

      const fallbackRoute = buildDemoRoute(waypoints, normalizedTransport)
      applyRouteResult(fallbackRoute, waypoints, true)
      routeWarning.value = `真实路网规划失败，已展示直线估算：${err.message || '请求失败'}`
      return fallbackRoute
    } finally {
      if (activeRouteController === controller) activeRouteController = null
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
    routeWarning,
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
    cancelRoutePlanning,
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
