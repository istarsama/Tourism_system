<template>
  <div class="map-canvas-container">
    <canvas 
      ref="canvasRef" 
      @mousedown="handleMouseDown"
      @mousemove="handleMouseMove"
      @mouseup="handleMouseUp"
      @mouseleave="handleMouseLeave"
      @wheel="handleWheel"
      @click="handleClick"
    />
    <div v-if="mapStore.loading" class="loading">地图加载中...</div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import { useMapStore } from '../stores/map'

const mapStore = useMapStore()
const canvasRef = ref(null)
const ctx = ref(null)
const mapImage = ref(null)

// 交互状态
const isDragging = ref(false)
const lastMouseX = ref(0)
const lastMouseY = ref(0)
const dragDistance = ref(0)

// 动画状态
const animationFrame = ref(null)
const pathAnimation = ref({
  active: false,
  progress: 0,
  speed: 50.0  // 加快动画速度
})

// 常量
const NODE_RADIUS = 6
const COLORS = {
  default: '#3b82f6',
  start: '#10b981',
  end: '#ef4444',
  path: '#f59e0b',
  edge: '#cbd5e1',
  edgePath: '#f59e0b'
}

onMounted(() => {
  initCanvas()
  loadMap()
  startAnimationLoop()
})

onUnmounted(() => {
  if (animationFrame.value) {
    cancelAnimationFrame(animationFrame.value)
  }
})

// 监听路径变化，触发动画
watch(() => mapStore.currentPath, (newPath) => {
  if (newPath && newPath.length > 0) {
    pathAnimation.value = {
      active: true,
      progress: 0,
      speed: 150.0  // 加快动画速度
    }
  } else {
    pathAnimation.value.active = false
  }
  render()  // 立即重绘
})

// 监听起点终点变化，立即重绘
watch(() => [mapStore.startNode, mapStore.endNode], () => {
  render()
}, { deep: true })

// 初始化 Canvas
function initCanvas() {
  const canvas = canvasRef.value
  if (!canvas) return

  ctx.value = canvas.getContext('2d')
  resizeCanvas()
  window.addEventListener('resize', resizeCanvas)
}

function resizeCanvas() {
  const canvas = canvasRef.value
  if (!canvas) return

  canvas.width = canvas.parentElement.clientWidth
  canvas.height = canvas.parentElement.clientHeight
  
  fitMapToScreen()
  render()
}

// 加载地图数据
async function loadMap() {
  await mapStore.loadGraph()
  
  // 加载地图背景图
  mapImage.value = new Image()
  // Vite 会自动从 public 目录提供静态文件
  mapImage.value.src = '/map.png'
  mapImage.value.onerror = () => {
    console.error('地图图片加载失败，路径:', mapImage.value.src)
  }
  mapImage.value.onload = () => {
    console.log('地图图片加载成功')
    fitMapToScreen()
    render()
  }
}

// 自适应缩放
function fitMapToScreen() {
  const canvas = canvasRef.value
  if (!canvas || !mapImage.value || !mapImage.value.complete) return

  const imgW = mapImage.value.width
  const imgH = mapImage.value.height
  const canvasW = canvas.width
  const canvasH = canvas.height

  const scaleX = canvasW / imgW
  const scaleY = canvasH / imgH
  const scale = Math.min(scaleX, scaleY) * 0.95

  mapStore.updateTransform({
    scale: scale,
    offsetX: (canvasW - imgW * scale) / 2,
    offsetY: (canvasH - imgH * scale) / 2
  })
}

// 坐标转换
function toScreen(x, y) {
  const t = mapStore.transform
  return {
    x: x * t.scale + t.offsetX,
    y: y * t.scale + t.offsetY
  }
}

function toWorld(screenX, screenY) {
  const t = mapStore.transform
  return {
    x: (screenX - t.offsetX) / t.scale,
    y: (screenY - t.offsetY) / t.scale
  }
}

// 鼠标事件处理
function handleMouseDown(e) {
  isDragging.value = true
  lastMouseX.value = e.clientX
  lastMouseY.value = e.clientY
  dragDistance.value = 0
}

function handleMouseMove(e) {
  if (!isDragging.value) return

  const dx = e.clientX - lastMouseX.value
  const dy = e.clientY - lastMouseY.value
  dragDistance.value += Math.abs(dx) + Math.abs(dy)

  const t = mapStore.transform
  mapStore.updateTransform({
    offsetX: t.offsetX + dx,
    offsetY: t.offsetY + dy
  })

  lastMouseX.value = e.clientX
  lastMouseY.value = e.clientY
  render()
}

function handleMouseUp() {
  isDragging.value = false
}

function handleMouseLeave() {
  isDragging.value = false
}

function handleWheel(e) {
  e.preventDefault()
  
  const rect = canvasRef.value.getBoundingClientRect()
  const mouseX = e.clientX - rect.left
  const mouseY = e.clientY - rect.top

  const t = mapStore.transform
  const worldBefore = toWorld(mouseX, mouseY)
  
  const scaleFactor = e.deltaY < 0 ? 1.1 : 0.9
  const newScale = Math.max(0.1, Math.min(5, t.scale * scaleFactor))
  
  const worldAfter = {
    x: (mouseX - t.offsetX) / newScale,
    y: (mouseY - t.offsetY) / newScale
  }
  
  mapStore.updateTransform({
    scale: newScale,
    offsetX: t.offsetX + (worldAfter.x - worldBefore.x) * newScale,
    offsetY: t.offsetY + (worldAfter.y - worldBefore.y) * newScale
  })
  
  render()
}

function handleClick(e) {
  if (dragDistance.value > 5) return // 拖拽操作，不触发点击

  const rect = canvasRef.value.getBoundingClientRect()
  const mouseX = e.clientX - rect.left
  const mouseY = e.clientY - rect.top
  const worldPos = toWorld(mouseX, mouseY)

  // 查找点击的节点
  for (const node of mapStore.nodes) {
    if (node.type !== 'spot') continue
    
    const screenPos = toScreen(node.x, node.y)
    const dist = Math.hypot(screenPos.x - mouseX, screenPos.y - mouseY)
    
    if (dist <= NODE_RADIUS + 3) {
      handleNodeClick(node, e.ctrlKey || e.metaKey)
      return
    }
  }
}

function handleNodeClick(node, isCtrlPressed) {
  mapStore.selectNode(node)
  
  // 状态机逻辑：
  // 1. 如果点击的是当前起点 -> 取消起点
  // 2. 如果点击的是当前终点 -> 取消终点
  // 3. 如果点击的是其他景点：
  //    - 没有起点 -> 设为起点
  //    - 有起点但没终点 -> 设为终点
  //    - 起点终点都有 -> 修改终点
  
  const isStartNode = mapStore.startNode && mapStore.startNode.id === node.id
  const isEndNode = mapStore.endNode && mapStore.endNode.id === node.id
  
  if (isStartNode) {
    // 点击起点 -> 取消起点
    mapStore.setStart(null)
  } else if (isEndNode) {
    // 点击终点 -> 取消终点
    mapStore.setEnd(null)
  } else {
    // 点击其他景点
    if (!mapStore.startNode) {
      // 没有起点 -> 设为起点
      mapStore.setStart(node)
    } else if (!mapStore.endNode) {
      // 有起点但没终点 -> 设为终点
      mapStore.setEnd(node)
    } else {
      // 起点终点都有 -> 修改终点
      mapStore.setEnd(node)
    }
  }
  
  render()
}

// 渲染函数
function render() {
  const canvas = canvasRef.value
  const context = ctx.value
  if (!canvas || !context) return

  context.clearRect(0, 0, canvas.width, canvas.height)

  // 1. 绘制地图背景
  if (mapImage.value && mapImage.value.complete) {
    const t = mapStore.transform
    const imgW = mapImage.value.width
    const imgH = mapImage.value.height
    
    context.drawImage(
      mapImage.value,
      t.offsetX,
      t.offsetY,
      imgW * t.scale,
      imgH * t.scale
    )
  }

  // 2. 绘制边
  context.strokeStyle = COLORS.edge
  context.lineWidth = 2
  
  for (const edge of mapStore.edges) {
    const nodeU = mapStore.nodeMap[edge.u]
    const nodeV = mapStore.nodeMap[edge.v]
    if (!nodeU || !nodeV) continue

    const posU = toScreen(nodeU.x, nodeU.y)
    const posV = toScreen(nodeV.x, nodeV.y)

    // 高亮路径上的边
    if (isEdgeInPath(edge.u, edge.v)) {
      context.strokeStyle = COLORS.edgePath
      context.lineWidth = 4
    } else {
      context.strokeStyle = COLORS.edge
      context.lineWidth = 2
    }

    context.beginPath()
    context.moveTo(posU.x, posU.y)
    context.lineTo(posV.x, posV.y)
    context.stroke()
  }

  // 3. 绘制路径动画
  if (pathAnimation.value.active && mapStore.pathCoords.length > 0) {
    drawAnimatedPath(context)
  }

  // 4. 绘制节点
  for (const node of mapStore.nodes) {
    if (node.type !== 'spot') continue

    const pos = toScreen(node.x, node.y)
    let color = COLORS.default

    if (mapStore.startNode && node.id === mapStore.startNode.id) {
      color = COLORS.start
    } else if (mapStore.endNode && node.id === mapStore.endNode.id) {
      color = COLORS.end
    } else if (mapStore.currentPath.includes(node.id)) {
      color = COLORS.path
    }

    context.fillStyle = color
    context.beginPath()
    context.arc(pos.x, pos.y, NODE_RADIUS, 0, Math.PI * 2)
    context.fill()

    // 选中节点加边框
    if (mapStore.selectedSpot && node.id === mapStore.selectedSpot.id) {
      context.strokeStyle = '#fff'
      context.lineWidth = 2
      context.stroke()
    }
  }
}

function drawAnimatedPath(context) {
  const coords = mapStore.pathCoords
  if (coords.length < 2) return

  const progress = pathAnimation.value.progress
  
  context.strokeStyle = COLORS.path
  context.lineWidth = 6
  context.lineCap = 'round'
  context.shadowColor = 'rgba(245, 158, 11, 0.5)'
  context.shadowBlur = 10

  context.beginPath()
  const start = toScreen(coords[0][0], coords[0][1])
  context.moveTo(start.x, start.y)

  let totalLength = 0
  const segments = []
  
  for (let i = 1; i < coords.length; i++) {
    const p1 = coords[i - 1]
    const p2 = coords[i]
    const len = Math.hypot(p2[0] - p1[0], p2[1] - p1[1])
    segments.push({ from: p1, to: p2, length: len })
    totalLength += len
  }

  let drawn = 0
  for (const seg of segments) {
    const segProgress = Math.min(1, Math.max(0, (progress - drawn) / seg.length))
    
    if (segProgress <= 0) break
    
    const from = toScreen(seg.from[0], seg.from[1])
    const to = toScreen(seg.to[0], seg.to[1])
    
    const currentX = from.x + (to.x - from.x) * segProgress
    const currentY = from.y + (to.y - from.y) * segProgress
    
    context.lineTo(currentX, currentY)
    
    if (segProgress < 1) break
    drawn += seg.length
  }

  context.stroke()
  context.shadowBlur = 0

  // 绘制动画指示点
  if (progress < totalLength) {
    let accum = 0
    for (const seg of segments) {
      if (progress < accum + seg.length) {
        const t = (progress - accum) / seg.length
        const x = seg.from[0] + (seg.to[0] - seg.from[0]) * t
        const y = seg.from[1] + (seg.to[1] - seg.from[1]) * t
        const pos = toScreen(x, y)

        context.fillStyle = '#fff'
        context.beginPath()
        context.arc(pos.x, pos.y, 8, 0, Math.PI * 2)
        context.fill()
        break
      }
      accum += seg.length
    }
  }
}

function isEdgeInPath(u, v) {
  const path = mapStore.currentPath
  for (let i = 0; i < path.length - 1; i++) {
    if ((path[i] === u && path[i + 1] === v) || 
        (path[i] === v && path[i + 1] === u)) {
      return true
    }
  }
  return false
}

// 动画循环
function startAnimationLoop() {
  let lastTime = 0
  
  const loop = (timestamp) => {
    const deltaTime = timestamp - lastTime
    lastTime = timestamp

    if (pathAnimation.value.active) {
      const coords = mapStore.pathCoords
      if (coords.length >= 2) {
        let totalLength = 0
        for (let i = 1; i < coords.length; i++) {
          const p1 = coords[i - 1]
          const p2 = coords[i]
          totalLength += Math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        }

        pathAnimation.value.progress += pathAnimation.value.speed * (deltaTime / 1000)
        
        if (pathAnimation.value.progress >= totalLength) {
          pathAnimation.value.progress = totalLength
          pathAnimation.value.active = false
        }
        
        render()
      }
    }

    animationFrame.value = requestAnimationFrame(loop)
  }

  animationFrame.value = requestAnimationFrame(loop)
}
</script>

<style scoped>
.map-canvas-container {
  position: relative;
  width: 100%;
  height: 100%;
  background: #e5e7eb;
  overflow: hidden;
}

canvas {
  display: block;
  cursor: grab;
  width: 100%;
  height: 100%;
}

canvas:active {
  cursor: grabbing;
}

.loading {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: rgba(255, 255, 255, 0.9);
  padding: 20px 30px;
  border-radius: 8px;
  font-weight: bold;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}
</style>
