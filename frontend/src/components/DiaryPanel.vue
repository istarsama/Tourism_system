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
<<<<<<< HEAD
        
        <!-- 发布日记按钮 -->
        <button 
          v-if="authStore.isAuthenticated" 
          class="btn-sm btn-primary" 
          @click="showCreateModal = true"
        >
          ✍️ 发布日记
        </button>
=======
>>>>>>> 3e1bb36431b7a0f07065b1556bbc344ad7fc5b10
      </div>
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
<<<<<<< HEAD
        <!-- 小红书风格：左侧缩略图 + 右侧信息 -->
        <div class="diary-layout">
          <!-- 封面图：显示第一张图片 -->
          <div v-if="diary.media_files && diary.media_files.length > 0" class="diary-thumbnail">
            <img :src="diary.media_files[0]" :alt="diary.title" />
            <!-- 图片数量标签 -->
            <span v-if="diary.media_files.length > 1" class="image-count">
              📷 {{ diary.media_files.length }}
            </span>
          </div>
          
          <!-- 文字信息区 -->
          <div class="diary-info">
            <h4>{{ diary.title }}</h4>
            <div class="diary-meta">
              <span>{{ diary.user_name }}</span>
              <span>⭐ {{ diary.score?.toFixed(1) || 'N/A' }}</span>
              <span>👁️ {{ diary.view_count || 0 }}</span>
            </div>
          </div>
=======
        <h4>{{ diary.title }}</h4>
        <div class="diary-meta">
          <span>{{ diary.user_name }}</span>
          <span>⭐ {{ diary.score?.toFixed(1) || 'N/A' }}</span>
          <span>👁️ {{ diary.view_count || 0 }}</span>
>>>>>>> 3e1bb36431b7a0f07065b1556bbc344ad7fc5b10
        </div>
      </div>
    </div>

<<<<<<< HEAD
    <!-- 发布日记模态框 -->
    <CreateDiaryModal 
      v-model:show="showCreateModal" 
      @success="handleCreateSuccess"
=======
    <!-- 日记详情模态框 -->
    <DiaryDetailModal
      v-model:show="showDetailModal"
      :diary-id="selectedDiaryId"
>>>>>>> 3e1bb36431b7a0f07065b1556bbc344ad7fc5b10
    />
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
<<<<<<< HEAD
import { useRouter } from 'vue-router'
import { useDiaryStore } from '../stores/diary'
import { useAuthStore } from '../stores/auth'
import CreateDiaryModal from './CreateDiaryModal.vue'
=======
import { useDiaryStore } from '../stores/diary'
import DiaryDetailModal from './DiaryDetailModal.vue'
>>>>>>> 3e1bb36431b7a0f07065b1556bbc344ad7fc5b10

const props = defineProps({
  spotId: Number  // 如果传入了景点ID，则只显示该景点的日记
})

const emit = defineEmits(['clear-spot-filter'])

<<<<<<< HEAD
const router = useRouter()
const diaryStore = useDiaryStore()
const authStore = useAuthStore()

const searchQuery = ref('')
const sortBy = ref('latest')
const showCreateModal = ref(false)
=======
const diaryStore = useDiaryStore()
const searchQuery = ref('')
const sortBy = ref('latest')
const showDetailModal = ref(false)
const selectedDiaryId = ref(null)
>>>>>>> 3e1bb36431b7a0f07065b1556bbc344ad7fc5b10

onMounted(() => {
  loadDiaries()
})

watch(() => props.spotId, () => {
  if (props.spotId) {
    loadDiaries()
  }
})

async function loadDiaries() {
  const params = {
    sort_by: sortBy.value
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
<<<<<<< HEAD
  // 使用路由跳转到日记详情页
  router.push(`/diary/${id}`)
}

function handleCreateSuccess() {
  // 发布成功后刷新列表
  loadDiaries()
=======
  selectedDiaryId.value = id
  showDetailModal.value = true
>>>>>>> 3e1bb36431b7a0f07065b1556bbc344ad7fc5b10
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
<<<<<<< HEAD
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

/* 小红书风格布局：左图右文 */
.diary-layout {
  display: flex;
  gap: 12px;
}

/* 缩略图容器 */
.diary-thumbnail {
  position: relative;
  width: 80px;
  height: 80px;
  flex-shrink: 0;
  border-radius: 6px;
  overflow: hidden;
  background: #e5e7eb;
}

.diary-thumbnail img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s;
}

.diary-item:hover .diary-thumbnail img {
  transform: scale(1.05);
}

/* 图片数量标签 */
.image-count {
  position: absolute;
  bottom: 4px;
  right: 4px;
  background: rgba(0, 0, 0, 0.6);
  color: white;
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 10px;
  font-weight: 500;
}

/* 文字信息区 */
.diary-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  min-width: 0;
=======
>>>>>>> 3e1bb36431b7a0f07065b1556bbc344ad7fc5b10
}

.diary-item h4 {
  margin: 0 0 8px 0;
  color: var(--primary-color);
  font-size: 15px;
  font-weight: 600;
<<<<<<< HEAD
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
=======
>>>>>>> 3e1bb36431b7a0f07065b1556bbc344ad7fc5b10
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
