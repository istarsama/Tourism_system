<template>
  <div class="diary-panel">
    <div class="diary-controls">
      <div>
        <h3 class="panel-title">全站笔记搜索</h3>
        <p class="panel-subtitle">可搜索校园与全国景点笔记，支持 demo 数据兜底。</p>
      </div>

      <div class="search-box">
        <input v-model="searchQuery" type="text" placeholder="搜索北京、杭州、教学楼厕所、自动售卖机..." @keyup.enter="handleSearch" />
        <button class="btn-sm btn-primary" @click="handleSearch">搜索</button>
      </div>

      <div class="filter-row">
        <select v-model="sortBy" @change="loadDiaries">
          <option value="heat">最热笔记</option>
          <option value="latest">最新发布</option>
          <option value="score">评分最高</option>
        </select>
        <button class="btn-sm btn-outline" @click="loadDiaries">刷新</button>
        <button v-if="authStore.isAuthenticated" class="btn-sm btn-primary" @click="showCreateModal = true">发布</button>
      </div>

      <p v-if="!authStore.isAuthenticated" class="auth-hint">登录后可发布日记</p>
      <p v-if="usingDemoFallback" class="demo-hint">当前包含演示补充笔记，用于搜索和路线 demo 验证。</p>
    </div>

    <div class="diary-list">
      <div v-if="diaryStore.loading" class="loading-message">加载中...</div>
      <div v-else-if="displayDiaries.length === 0" class="empty-message">暂无日记</div>

      <div v-else v-for="diary in displayDiaries" :key="diary.id" class="diary-item" @click="handleViewDiary(diary)">
        <div class="diary-title-row">
          <h4>{{ diary.title }}</h4>
          <span class="scope-badge" :class="diary.scope === 'national' ? 'national' : 'campus'">
            {{ diary.scope === 'national' ? '全国' : '校园' }}
          </span>
        </div>
        <p class="diary-snippet">{{ diary.content }}</p>
        <div class="diary-meta">
          <span>{{ diary.user_name }}</span>
          <span>评分 {{ Number(diary.score || 0).toFixed(1) }}</span>
          <span>热度 {{ diary.view_count || 0 }}</span>
        </div>
      </div>
    </div>

    <DiaryDetailModal v-model:show="showDetailModal" :diary-id="selectedDiaryId" />

    <div v-if="selectedDemoDiary" class="demo-modal" @click="selectedDemoDiary = null">
      <div class="demo-card" @click.stop>
        <div class="demo-card-header">
          <h3>{{ selectedDemoDiary.title }}</h3>
          <button @click="selectedDemoDiary = null">×</button>
        </div>
        <p class="demo-card-meta">{{ selectedDemoDiary.user_name }} · {{ selectedDemoDiary.scope === 'national' ? '全国笔记' : '校园笔记' }}</p>
        <p class="demo-card-content">{{ selectedDemoDiary.content }}</p>
      </div>
    </div>

    <CreateDiaryModal v-model:show="showCreateModal" @success="handleCreateSuccess" />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useDiaryStore } from '../stores/diary'
import { useAuthStore } from '../stores/auth'
import DiaryDetailModal from './DiaryDetailModal.vue'
import CreateDiaryModal from './CreateDiaryModal.vue'
import { searchDemoDiaries } from '../data/diaryDemo'

const diaryStore = useDiaryStore()
const authStore = useAuthStore()
const searchQuery = ref('')
const sortBy = ref('heat')
const showDetailModal = ref(false)
const showCreateModal = ref(false)
const selectedDiaryId = ref(null)
const selectedDemoDiary = ref(null)
const fallbackDiaries = ref([])
const usingDemoFallback = ref(false)

const displayDiaries = computed(() => {
  const seen = new Set()
  return [...diaryStore.diaries, ...fallbackDiaries.value].filter((diary) => {
    const key = `${diary.id}`
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
})

onMounted(() => {
  loadDiaries()
})

async function loadDiaries() {
  const params = { sort_by: sortBy.value, scope: 'all' }
  if (searchQuery.value.trim()) params.keyword = searchQuery.value.trim()

  usingDemoFallback.value = false
  fallbackDiaries.value = []

  const demoMatches = searchDemoDiaries(searchQuery.value, sortBy.value)
  try {
    const results = await diaryStore.loadDiaries(params)
    if (!Array.isArray(results) || results.length === 0 || searchQuery.value.trim()) {
      fallbackDiaries.value = demoMatches
      usingDemoFallback.value = demoMatches.length > 0
    }
  } catch (error) {
    console.error('Failed to load diaries, using demo fallback:', error)
    fallbackDiaries.value = demoMatches
    usingDemoFallback.value = demoMatches.length > 0
  }
}

function handleSearch() {
  loadDiaries()
}

function handleViewDiary(diary) {
  if (typeof diary.id === 'string' && diary.id.startsWith('demo-')) {
    selectedDemoDiary.value = diary
    return
  }
  selectedDiaryId.value = diary.id
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

.diary-controls {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.panel-title {
  margin: 0;
  color: #111827;
  font-size: 16px;
  font-weight: 800;
}

.panel-subtitle,
.demo-hint,
.auth-hint {
  margin: 4px 0 0;
  color: #6b7280;
  font-size: 12px;
  line-height: 1.5;
}

.demo-hint {
  color: #b45309;
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
  border-radius: 8px;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.2s;
}

.diary-item:hover {
  border-color: var(--primary-color);
  background: var(--hover-bg);
  transform: translateY(-1px);
}

.diary-title-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}

.diary-item h4 {
  margin: 0 0 8px 0;
  color: var(--primary-color);
  font-size: 15px;
  font-weight: 700;
  line-height: 1.35;
}

.scope-badge {
  flex-shrink: 0;
  border-radius: 999px;
  padding: 2px 7px;
  font-size: 11px;
  font-weight: 700;
  background: #dcfce7;
  color: #166534;
}

.scope-badge.national {
  background: #dbeafe;
  color: #1d4ed8;
}

.diary-snippet {
  margin: 0 0 10px;
  color: #4b5563;
  font-size: 13px;
  line-height: 1.55;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.diary-meta {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  font-size: 12px;
  color: #6b7280;
}

.demo-modal {
  position: fixed;
  inset: 0;
  z-index: 2000;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.demo-card {
  width: min(520px, 100%);
  border-radius: 12px;
  background: white;
  padding: 18px;
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.25);
}

.demo-card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.demo-card-header h3 {
  margin: 0;
  color: #003d74;
  font-size: 18px;
}

.demo-card-header button {
  padding: 2px 8px;
  background: #f1f5f9;
  color: #475569;
}

.demo-card-meta {
  color: #64748b;
  font-size: 12px;
  margin: 8px 0 12px;
}

.demo-card-content {
  color: #334155;
  font-size: 14px;
  line-height: 1.8;
  margin: 0;
}
</style>
