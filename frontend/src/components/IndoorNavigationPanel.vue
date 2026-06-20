<template>
  <div class="space-y-4">
    <div class="bg-gradient-to-br from-white/80 to-white/60 backdrop-blur-sm rounded-2xl p-5 ring-1 ring-black/5 shadow-lg">
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-sm font-bold text-gray-800">教学楼室内导航</h3>
        <button class="text-xs text-bupt-blue font-semibold" @click="handleReset">重置</button>
      </div>

      <div class="space-y-3">
        <div>
          <label class="block text-xs font-semibold text-gray-600 mb-1">起点</label>
          <SearchInput
            v-model="startSearch"
            placeholder="搜索入口、中庭、教室..."
            :selected="store.startNode"
            :search-fn="searchIndoor"
            @select="handleStartSelect"
          />
        </div>

        <div>
          <label class="block text-xs font-semibold text-gray-600 mb-1">终点</label>
          <SearchInput
            v-model="endSearch"
            placeholder="搜索厕所、楼梯、售卖机..."
            :selected="store.endNode"
            :search-fn="searchIndoor"
            @select="handleEndSelect"
          />
        </div>

        <button
          class="w-full px-3 py-2 rounded-lg bg-bupt-blue text-white text-sm font-semibold disabled:opacity-50"
          :disabled="!store.canNavigate"
          @click="store.navigate"
        >
          开始室内导航
        </button>
      </div>
    </div>

    <div class="bg-white/75 rounded-2xl p-4 ring-1 ring-black/5">
      <h4 class="text-sm font-bold text-gray-800 mb-3">常用地标</h4>
      <div class="grid grid-cols-2 gap-2">
        <button
          v-for="node in quickNodes"
          :key="node.id"
          class="quick-btn"
          @click="store.setSelectedNode(node)"
        >
          {{ node.name }}
        </button>
      </div>
    </div>

    <div v-if="store.hasPath" class="bg-blue-50/75 rounded-2xl p-4 ring-1 ring-blue-100">
      <h4 class="text-sm font-bold text-bupt-blue mb-2">室内路线结果</h4>
      <div class="text-sm text-gray-700 space-y-1 mb-3">
        <p>总距离：{{ store.totalDistanceM.toFixed(0) }} m</p>
        <p>预计耗时：{{ Math.max(1, Math.round(store.estimatedDurationS / 60)) }} 分钟</p>
        <p>途径：{{ store.pathNodes.map((node) => node.name).join(' → ') }}</p>
      </div>
      <ol class="space-y-2">
        <li v-for="(step, index) in store.instructions" :key="step.id" class="step-item">
          <span>{{ index + 1 }}</span>
          <p>{{ step.text }}</p>
        </li>
      </ol>
    </div>

    <div v-if="store.selectedNode" class="bg-emerald-50/75 rounded-2xl p-4 ring-1 ring-emerald-100">
      <h4 class="text-sm font-bold text-emerald-700 mb-1">{{ store.selectedNode.name }}</h4>
      <p class="text-xs text-gray-600 leading-5 mb-3">{{ store.selectedNode.detail }}</p>
      <div class="grid grid-cols-2 gap-2">
        <button class="mini-action" @click="store.setStartNode(store.selectedNode)">设为起点</button>
        <button class="mini-action" @click="store.setEndNode(store.selectedNode)">设为终点</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import SearchInput from './SearchInput.vue'
import { useIndoorMapStore } from '../stores/indoorMap'

const store = useIndoorMapStore()
const startSearch = ref('')
const endSearch = ref('')

const quickNodes = computed(() =>
  store.nodes.filter((node) => ['gate', 'vending', 'toilet', 'stairs-east', 'elevator', 'office'].includes(node.id))
)

function searchIndoor(query) {
  return store.searchLandmarks(query, 8)
}

function handleStartSelect(node) {
  store.setStartNode(node)
  startSearch.value = node?.name || ''
}

function handleEndSelect(node) {
  store.setEndNode(node)
  endSearch.value = node?.name || ''
}

function handleReset() {
  startSearch.value = ''
  endSearch.value = ''
  store.resetNavigation()
}
</script>

<style scoped>
.bg-bupt-blue {
  background-color: #003d74;
}

.text-bupt-blue {
  color: #003d74;
}

.quick-btn,
.mini-action {
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.82);
  color: #334155;
  padding: 8px 10px;
  font-size: 12px;
  border: 1px solid rgba(148, 163, 184, 0.35);
}

.quick-btn:hover,
.mini-action:hover {
  background: #eff6ff;
  color: #003d74;
}

.step-item {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  font-size: 13px;
  color: #475569;
}

.step-item span {
  width: 20px;
  height: 20px;
  border-radius: 999px;
  background: #003d74;
  color: white;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  flex: 0 0 auto;
}

.step-item p {
  margin: 0;
  line-height: 1.6;
}
</style>
