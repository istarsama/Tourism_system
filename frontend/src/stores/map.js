import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api } from '../api'

export const useMapStore = defineStore('map', () => {
  // 地图数据
  const nodes = ref([])
  const edges = ref([])
  const nodeMap = ref({})
  const loading = ref(false)
  const error = ref(null)

  // 导航状态
  const startNode = ref(null)
  const endNode = ref(null)
  const currentPath = ref([])
  const pathCoords = ref([])
  const totalCost = ref(0)
  const costUnit = ref('米')

  // 选中的景点
  const selectedSpot = ref(null)

  // 地图视图变换
  const transform = ref({
    scale: 1,
    offsetX: 0,
    offsetY: 0,
  })

  // 计算属性
  const canNavigate = computed(() => startNode.value && endNode.value)
  const hasPath = computed(() => currentPath.value.length > 0)

  // 加载地图数据
  async function loadGraph() {
    loading.value = true
    error.value = null
    try {
      const data = await api.getGraph()
      nodes.value = data.nodes
      edges.value = data.edges
      
      // 构建节点映射
      const map = {}
      data.nodes.forEach(node => {
        map[node.id] = node
      })
      nodeMap.value = map
    } catch (err) {
      error.value = err.message
      console.error('Failed to load graph:', err)
    } finally {
      loading.value = false
    }
  }

  // 搜索景点
  async function searchSpots(query) {
    if (!query) return []
    try {
      const results = await api.searchSpots(query)
      return results
    } catch (err) {
      console.error('Search failed:', err)
      return []
    }
  }

  // 执行导航
  async function navigate(strategy = 'dist', transport = 'walk') {
    if (!canNavigate.value) return

    try {
      const result = await api.navigate({
        start_id: startNode.value.id,
        end_id: endNode.value.id,
        strategy,
        transport,
      })

      currentPath.value = result.path_ids
      pathCoords.value = result.path_coords
      totalCost.value = result.total_cost
      costUnit.value = result.cost_unit

      return result
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  // 重置导航
  function resetNavigation() {
    startNode.value = null
    endNode.value = null
    currentPath.value = []
    pathCoords.value = []
    totalCost.value = 0
    selectedSpot.value = null
  }

  // 选择节点
  function selectNode(node) {
    selectedSpot.value = node
  }

  // 设置起点
  function setStart(node) {
    startNode.value = node
    // 清除路径
    if (currentPath.value.length > 0) {
      currentPath.value = []
      pathCoords.value = []
      totalCost.value = 0
    }
  }

  // 设置终点
  function setEnd(node) {
    endNode.value = node
    // 清除路径
    if (currentPath.value.length > 0) {
      currentPath.value = []
      pathCoords.value = []
      totalCost.value = 0
    }
  }

  // 更新视图变换
  function updateTransform(newTransform) {
    transform.value = { ...transform.value, ...newTransform }
  }

  return {
    // 状态
    nodes,
    edges,
    nodeMap,
    loading,
    error,
    startNode,
    endNode,
    currentPath,
    pathCoords,
    totalCost,
    costUnit,
    selectedSpot,
    transform,
    
    // 计算属性
    canNavigate,
    hasPath,
    
    // 方法
    loadGraph,
    searchSpots,
    navigate,
    resetNavigation,
    selectNode,
    setStart,
    setEnd,
    updateTransform,
  }
})
