<template>
  <div class="indoor-map-container">
    <svg viewBox="0 0 880 520" class="indoor-map" role="img" aria-label="教学楼室内导航图">
      <rect x="35" y="65" width="810" height="390" rx="8" class="building-shell" />
      <rect x="75" y="210" width="720" height="95" rx="8" class="main-corridor" />
      <rect x="160" y="95" width="520" height="70" rx="8" class="side-corridor" />
      <rect x="485" y="315" width="310" height="75" rx="8" class="side-corridor" />

      <line
        v-for="edge in store.edges"
        :key="`${edge.u}-${edge.v}`"
        :x1="store.nodeMap[edge.u]?.x"
        :y1="store.nodeMap[edge.u]?.y"
        :x2="store.nodeMap[edge.v]?.x"
        :y2="store.nodeMap[edge.v]?.y"
        class="edge-line"
        :class="{ active: isEdgeInPath(edge.u, edge.v) }"
      />

      <polyline
        v-if="pathPoints"
        :points="pathPoints"
        class="route-line"
      />

      <g
        v-for="node in store.nodes"
        :key="node.id"
        class="node"
        :class="nodeClass(node)"
        @click="store.handleNodePick(node)"
      >
        <circle :cx="node.x" :cy="node.y" r="13" />
        <text :x="node.x" :y="node.y - 22" text-anchor="middle">{{ node.name }}</text>
      </g>
    </svg>

    <div v-if="store.selectedNode" class="indoor-detail">
      <div>
        <p class="detail-kicker">当前点位</p>
        <h3>{{ store.selectedNode.name }}</h3>
        <p>{{ store.selectedNode.detail }}</p>
      </div>
      <div class="detail-actions">
        <button @click="store.setStartNode(store.selectedNode)">设为起点</button>
        <button @click="store.setEndNode(store.selectedNode)">设为终点</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useIndoorMapStore } from '../stores/indoorMap'

const store = useIndoorMapStore()

const pathPoints = computed(() => {
  if (!store.hasPath) return ''
  return store.pathNodes.map((node) => `${node.x},${node.y}`).join(' ')
})

function isEdgeInPath(u, v) {
  const path = store.currentPath
  for (let i = 1; i < path.length; i += 1) {
    if ((path[i - 1] === u && path[i] === v) || (path[i - 1] === v && path[i] === u)) {
      return true
    }
  }
  return false
}

function nodeClass(node) {
  return {
    start: store.startNode?.id === node.id,
    end: store.endNode?.id === node.id,
    selected: store.selectedNode?.id === node.id,
    route: store.currentPath.includes(node.id),
    service: ['service', 'toilet', 'stairs', 'elevator'].includes(node.type),
  }
}
</script>

<style scoped>
.indoor-map-container {
  position: absolute;
  inset: 0;
  background: #eef2f7;
  overflow: hidden;
}

.indoor-map {
  width: 100%;
  height: 100%;
}

.building-shell {
  fill: #f8fafc;
  stroke: #64748b;
  stroke-width: 2;
}

.main-corridor {
  fill: #e0f2fe;
  stroke: #bae6fd;
}

.side-corridor {
  fill: #ecfdf5;
  stroke: #bbf7d0;
}

.edge-line {
  stroke: #94a3b8;
  stroke-width: 5;
  stroke-linecap: round;
}

.edge-line.active {
  stroke: #f97316;
}

.route-line {
  fill: none;
  stroke: #ea580c;
  stroke-width: 9;
  stroke-linecap: round;
  stroke-linejoin: round;
  opacity: 0.78;
}

.node {
  cursor: pointer;
}

.node circle {
  fill: #2563eb;
  stroke: #fff;
  stroke-width: 4;
  filter: drop-shadow(0 6px 10px rgba(15, 23, 42, 0.18));
}

.node text {
  fill: #0f172a;
  font-size: 16px;
  font-weight: 700;
  paint-order: stroke;
  stroke: rgba(255, 255, 255, 0.9);
  stroke-width: 5px;
}

.node.service circle {
  fill: #0f766e;
}

.node.route circle {
  fill: #f59e0b;
}

.node.start circle {
  fill: #059669;
}

.node.end circle {
  fill: #dc2626;
}

.node.selected circle {
  stroke: #111827;
}

.indoor-detail {
  position: absolute;
  right: 24px;
  bottom: 24px;
  width: min(360px, calc(100% - 48px));
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(12px);
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 18px 45px rgba(15, 23, 42, 0.18);
  border: 1px solid rgba(148, 163, 184, 0.35);
}

.detail-kicker {
  margin: 0 0 4px;
  font-size: 12px;
  color: #64748b;
}

.indoor-detail h3 {
  margin: 0 0 8px;
  color: #003d74;
  font-size: 18px;
}

.indoor-detail p {
  margin: 0;
  color: #475569;
  font-size: 13px;
  line-height: 1.6;
}

.detail-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-top: 12px;
}

.detail-actions button {
  background: #e0f2fe;
  color: #075985;
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 12px;
}
</style>
