import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import {
  buildIndoorInstruction,
  indoorEdges,
  indoorNodes,
  indoorTypeLabels,
} from '../data/indoorDemo'

function buildAdjacency() {
  const adj = {}
  for (const node of indoorNodes) {
    adj[node.id] = []
  }
  for (const edge of indoorEdges) {
    adj[edge.u]?.push({ to: edge.v, distance: edge.distance })
    adj[edge.v]?.push({ to: edge.u, distance: edge.distance })
  }
  return adj
}

function scoreMatch(query, node) {
  const q = query.trim().toLowerCase()
  if (!q) return 0
  const target = `${node.name} ${node.type} ${indoorTypeLabels[node.type] || ''} ${node.detail}`.toLowerCase()
  if (target.includes(q)) return 96

  let hits = 0
  for (const ch of q) {
    if (target.includes(ch)) hits += 1
  }
  return Math.round((hits / Math.max(q.length, 1)) * 78)
}

function shortestPath(startId, endId) {
  const adj = buildAdjacency()
  const distances = Object.fromEntries(indoorNodes.map((node) => [node.id, Infinity]))
  const previous = Object.fromEntries(indoorNodes.map((node) => [node.id, null]))
  const queue = [{ id: startId, cost: 0 }]
  distances[startId] = 0

  while (queue.length) {
    queue.sort((a, b) => a.cost - b.cost)
    const current = queue.shift()
    if (!current || current.cost > distances[current.id]) continue
    if (current.id === endId) break

    for (const edge of adj[current.id] || []) {
      const nextCost = current.cost + edge.distance
      if (nextCost < distances[edge.to]) {
        distances[edge.to] = nextCost
        previous[edge.to] = current.id
        queue.push({ id: edge.to, cost: nextCost })
      }
    }
  }

  if (!Number.isFinite(distances[endId])) {
    return { pathIds: [], distance: 0 }
  }

  const pathIds = []
  let cursor = endId
  while (cursor) {
    pathIds.unshift(cursor)
    cursor = previous[cursor]
  }

  return { pathIds, distance: distances[endId] }
}

export const useIndoorMapStore = defineStore('indoorMap', () => {
  const nodes = ref(indoorNodes)
  const edges = ref(indoorEdges)
  const selectedNode = ref(null)
  const startNode = ref(null)
  const endNode = ref(null)
  const currentPath = ref([])
  const totalDistanceM = ref(0)

  const nodeMap = computed(() => Object.fromEntries(nodes.value.map((node) => [node.id, node])))
  const pathNodes = computed(() => currentPath.value.map((id) => nodeMap.value[id]).filter(Boolean))
  const estimatedDurationS = computed(() => Math.round(totalDistanceM.value / 1.2))
  const canNavigate = computed(() => startNode.value && endNode.value && startNode.value.id !== endNode.value.id)
  const hasPath = computed(() => currentPath.value.length > 1)
  const instructions = computed(() => {
    const result = []
    for (let i = 1; i < pathNodes.value.length; i += 1) {
      const from = pathNodes.value[i - 1]
      const to = pathNodes.value[i]
      result.push({
        id: `${from.id}-${to.id}`,
        text: buildIndoorInstruction(from, to),
      })
    }
    return result
  })

  function searchLandmarks(query, limit = 6) {
    if (!query?.trim()) return []
    return nodes.value
      .map((node) => ({ ...node, score: scoreMatch(query, node), scope: 'indoor' }))
      .filter((node) => node.score > 30)
      .sort((a, b) => b.score - a.score)
      .slice(0, limit)
  }

  function clearRoute() {
    currentPath.value = []
    totalDistanceM.value = 0
  }

  function setSelectedNode(node) {
    selectedNode.value = node || null
  }

  function setStartNode(node) {
    startNode.value = node || null
    if (startNode.value && endNode.value?.id === startNode.value.id) {
      endNode.value = null
    }
    clearRoute()
  }

  function setEndNode(node) {
    endNode.value = node || null
    if (endNode.value && startNode.value?.id === endNode.value.id) {
      startNode.value = null
    }
    clearRoute()
  }

  function navigate() {
    if (!canNavigate.value) return null
    const result = shortestPath(startNode.value.id, endNode.value.id)
    currentPath.value = result.pathIds
    totalDistanceM.value = result.distance
    return result
  }

  function resetNavigation() {
    selectedNode.value = null
    startNode.value = null
    endNode.value = null
    clearRoute()
  }

  function handleNodePick(node) {
    setSelectedNode(node)
    if (!startNode.value) {
      setStartNode(node)
    } else if (!endNode.value && startNode.value.id !== node.id) {
      setEndNode(node)
    }
  }

  return {
    nodes,
    edges,
    selectedNode,
    startNode,
    endNode,
    currentPath,
    totalDistanceM,
    nodeMap,
    pathNodes,
    estimatedDurationS,
    canNavigate,
    hasPath,
    instructions,
    searchLandmarks,
    setSelectedNode,
    setStartNode,
    setEndNode,
    navigate,
    resetNavigation,
    handleNodePick,
  }
})
