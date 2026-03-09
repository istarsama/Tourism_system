import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api } from '../api'

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

  const routeCoords = ref([])
  const nodeIds = ref([])
  const totalDistanceM = ref(0)
  const estimatedDurationS = ref(0)
  const routeCity = ref('')
  const routeTransport = ref('walk')
  const routeLoading = ref(false)
  const routeError = ref(null)

  const isInitializing = ref(false)

  const canNavigate = computed(() => startSpot.value && endSpot.value)
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
    routeCoords.value = []
    nodeIds.value = []
    totalDistanceM.value = 0
    estimatedDurationS.value = 0
    routeCity.value = ''
    routeError.value = null
  }

  function setStartSpot(spot) {
    startSpot.value = spot
    if (spot && endSpot.value && endSpot.value.id === spot.id) {
      endSpot.value = null
    }
    resetRoute()
  }

  function setEndSpot(spot) {
    endSpot.value = spot
    if (spot && startSpot.value && startSpot.value.id === spot.id) {
      startSpot.value = null
    }
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
    resetRoute()
  }

  async function navigateOsm(transport = 'walk') {
    if (!canNavigate.value) return null

    routeLoading.value = true
    routeError.value = null
    try {
      const result = await api.navigateOsm({
        start_spot_id: startSpot.value.id,
        end_spot_id: endSpot.value.id,
        transport,
      })

      routeCoords.value = result.path_coords || []
      nodeIds.value = result.node_ids || []
      totalDistanceM.value = result.total_distance_m || 0
      estimatedDurationS.value = result.estimated_duration_s || 0
      routeCity.value = result.city || ''
      routeTransport.value = result.transport || transport
      return result
    } catch (err) {
      routeError.value = err.message
      throw err
    } finally {
      routeLoading.value = false
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
    routeCoords,
    nodeIds,
    totalDistanceM,
    estimatedDurationS,
    routeCity,
    routeTransport,
    routeLoading,
    routeError,
    isInitializing,
    canNavigate,
    hasRoute,
    supportsSlippyMap,
    hasSpots,
    initialize,
    loadModeConfig,
    loadNationalSpots,
    setSelectedSpot,
    setStartSpot,
    setEndSpot,
    setStartSpotById,
    setEndSpotById,
    resetRoute,
    resetSelections,
  }
})
