<template>
  <div class="diary-panel">
    <!-- 景点过滤提示 -->
    <div v-if="spotId" class="spot-filter-hint">
      <span>正在查看该景点的日记</span>
      <button class="btn-sm btn-outline" @click="$emit('clear-spot-filter')">
        查看全部日记
      </button>
    </div>

    <!-- 搜索与筛选 -->
    <div class="diary-controls">
      <div class="search-box">
        <input
          v-model="searchQuery"
          type="text"
          placeholder="搜索日记..."
          @keyup.enter="handleSearch"
        />
        <button class="btn-sm btn-primary" @click="handleSearch">搜索</button>
      </div>
      
      <div class="filter-row">
        <select v-model="sortBy" @change="loadDiaries">
          <option value="latest">最新发布</option>
          <option value="heat">最热 (浏览量)</option>
          <option value="score">评分最高</option>
        </select>
        
        <button class="btn-sm btn-outline" @click="loadDiaries">
          🔄 刷新
        </button>

        <button
          v-if="authStore.isAuthenticated"
          class="btn-sm btn-primary"
          @click="showCreateModal = true"
        >
          ✍️ 发布
        </button>
      </div>

      <p v-if="!authStore.isAuthenticated" class="auth-hint">
        登录后可发布日记
      </p>
    </div>

    <!-- 日记列表 -->
    <div class="diary-list">
      <div v-if="diaryStore.loading" class="loading-message">
        加载中...
      </div>
      
      <div v-else-if="diaryStore.diaries.length === 0" class="empty-message">
        暂无日记
      </div>
      
      <div
        v-else
        v-for="diary in diaryStore.diaries"
        :key="diary.id"
        class="diary-item"
        @click="handleViewDiary(diary.id)"
      >
        <h4>{{ diary.title }}</h4>
        <div class="diary-meta">
          <span>{{ diary.user_name }}</span>
          <span>⭐ {{ diary.score?.toFixed(1) || 'N/A' }}</span>
          <span>👁️ {{ diary.view_count || 0 }}</span>
        </div>
      </div>
    </div>

    <!-- 日记详情模态框 -->
    <DiaryDetailModal
      v-model:show="showDetailModal"
      :diary-id="selectedDiaryId"
    />

    <CreateDiaryModal
      v-model:show="showCreateModal"
      :scope="publishScope"
      :preset-spot-id="spotId ?? null"
      @success="handleCreateSuccess"
    />
  </div>
</template>

<script setup>
import { computed, ref, onMounted, watch } from 'vue'
import { useDiaryStore } from '../stores/diary'
import { useAuthStore } from '../stores/auth'
import { useMapStore } from '../stores/map'
import DiaryDetailModal from './DiaryDetailModal.vue'
import CreateDiaryModal from './CreateDiaryModal.vue'

const props = defineProps({
  spotId: Number  // 如果传入了景点ID，则只显示该景点的日记
})

const emit = defineEmits(['clear-spot-filter'])

const diaryStore = useDiaryStore()
const authStore = useAuthStore()
const mapStore = useMapStore()
const searchQuery = ref('')
const sortBy = ref('latest')
const showDetailModal = ref(false)
const showCreateModal = ref(false)
const selectedDiaryId = ref(null)
const publishScope = computed(() => (mapStore.activeScope === 'national' ? 'national' : 'campus'))

onMounted(() => {
  loadDiaries()
})

watch(() => props.spotId, () => {
  loadDiaries()
})

watch(() => mapStore.activeScope, () => {
  loadDiaries()
})

async function loadDiaries() {
  const params = {
    sort_by: sortBy.value,
    scope: publishScope.value
  }
  
  if (searchQuery.value) {
    params.keyword = searchQuery.value
  }
  
  // 如果指定了景点ID，使用景点日记接口
  if (props.spotId) {
    await diaryStore.loadSpotDiaries(props.spotId, params)
  } else {
    await diaryStore.loadDiaries(params)
  }
}

function handleSearch() {
  loadDiaries()
}

function handleViewDiary(id) {
  selectedDiaryId.value = id
  showDetailModal.value = true
}

async function handleCreateSuccess() {
  await loadDiaries()
}
</script>

<style scoped>
.diary-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.spot-filter-hint {
  background: #dbeafe;
  border: 1px solid #93c5fd;
  border-radius: 6px;
  padding: 10px 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  color: #1e40af;
}

.diary-controls {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.search-box {
  display: flex;
  gap: 8px;
}

.search-box input {
  flex: 1;
}

.filter-row {
  display: flex;
  gap: 8px;
  align-items: center;
}

.filter-row select {
  flex: 1;
}

.auth-hint {
  margin: 0;
  color: #6b7280;
  font-size: 12px;
}

.diary-list {
  max-height: 500px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.loading-message,
.empty-message {
  text-align: center;
  color: #9ca3af;
  padding: 20px;
  font-size: 14px;
}

.diary-item {
  background: #f9fafb;
  padding: 12px;
  border-radius: 6px;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.2s;
}

.diary-item:hover {
  border-color: var(--primary-color);
  background: var(--hover-bg);
  transform: translateY(-1px);
}

.diary-item h4 {
  margin: 0 0 8px 0;
  color: var(--primary-color);
  font-size: 15px;
  font-weight: 600;
}

.diary-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: #6b7280;
}

.diary-meta span {
  display: flex;
  align-items: center;
  gap: 4px;
}
</style>
