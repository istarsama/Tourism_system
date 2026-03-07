<template>
  <!-- 始终使用 Teleport 模态框模式 -->
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="show && diary" class="modal-overlay" @click="handleClose">
        <div class="modal diary-detail-modal" @click.stop>
          <div class="modal-header">
            <h2>{{ diary.title }}</h2>
            <button class="btn-close" @click="handleClose">✕</button>
          </div>

          <div class="diary-meta">
            <span>作者: <b>{{ diary.user_name }}</b></span>
            <span>评分: ⭐ {{ diary.score?.toFixed(1) || 'N/A' }}</span>
            <span>热度: 👁️ {{ diary.view_count || 0 }}</span>
          </div>

          <div class="diary-content">
            {{ diary.content }}
          </div>

          <!-- 小红书风格图片网格 -->
          <div v-if="diary.media_files && diary.media_files.length > 0" class="diary-images-grid">
            <div 
              v-for="(url, index) in diary.media_files" 
              :key="index" 
              class="image-item"
              :class="getImageClass(diary.media_files.length, index)"
              @click="viewImage(url)"
            >
              <img :src="url" :alt="`图片 ${index + 1}`" loading="lazy" />
            </div>
          </div>

          <!-- 大图预览模态框 -->
          <Teleport to="body">
            <Transition name="fade">
              <div v-if="imageViewerVisible" class="image-viewer" @click="closeImageViewer">
                <img :src="currentImage" alt="大图预览" @click.stop />
                <button class="viewer-close" @click="closeImageViewer">✕</button>
              </div>
            </Transition>
          </Teleport>

          <hr />

          <h3>评论 ({{ comments.length }})</h3>
          
          <div class="comments-list">
            <div v-if="comments.length === 0" class="empty-message">
              暂无评论
            </div>
            
            <div v-else v-for="comment in comments" :key="comment.id" class="comment-item">
              <div class="comment-header">
                <span class="comment-author">{{ comment.user_name }}</span>
                <span class="comment-score">⭐ {{ comment.score }}</span>
              </div>
              <div class="comment-content">{{ comment.content }}</div>
            </div>
          </div>

          <!-- 发表评论 -->
          <div v-if="authStore.isAuthenticated" class="comment-form">
            <label>发表评论</label>
            <div class="score-input">
              打分: 
              <input
                v-model.number="commentScore"
                type="number"
                min="1"
                max="5"
                style="width: 60px; margin-left: 8px;"
              />
              / 5
            </div>
            <textarea
              v-model="commentContent"
              rows="3"
              placeholder="写下你的评论..."
            ></textarea>
            <button 
              class="btn-primary btn-sm" 
              @click="handleSubmitComment"
              :disabled="submitting"
            >
              {{ submitting ? '提交中...' : '提交评论' }}
            </button>
          </div>
          
          <div v-else class="login-hint">
            请登录后发表评论
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useDiaryStore } from '../stores/diary'
import { useAuthStore } from '../stores/auth'

const props = defineProps({
  show: Boolean,
  diaryId: Number
})

const emit = defineEmits(['update:show'])

const diaryStore = useDiaryStore()
const authStore = useAuthStore()

const diary = ref(null)
const comments = ref([])
const commentContent = ref('')
const commentScore = ref(5)
const submitting = ref(false)

// 图片查看器状态
const imageViewerVisible = ref(false)
const currentImage = ref('')

// 根据图片数量返回不同的布局类
function getImageClass(total, index) {
  if (total === 1) return 'single'
  if (total === 2) return 'double'
  if (total === 4) return 'quad'
  return 'grid' // 3张或5+张使用标准网格
}

// 查看大图
function viewImage(url) {
  currentImage.value = url
  imageViewerVisible.value = true
}

// 关闭大图
function closeImageViewer() {
  imageViewerVisible.value = false
}

watch(() => props.show, async (newVal) => {
  if (newVal && props.diaryId) {
    await loadDiaryDetail()
  }
})

watch(() => props.diaryId, async (newVal) => {
  if (newVal && props.show) {
    await loadDiaryDetail()
  }
})

async function loadDiaryDetail() {
  try {
    diary.value = await diaryStore.loadDiary(props.diaryId)
    comments.value = await diaryStore.loadComments(props.diaryId)
  } catch (error) {
    alert('加载日记失败: ' + error.message)
    handleClose()
  }
}

async function handleSubmitComment() {
  if (!commentContent.value.trim()) {
    alert('请输入评论内容')
    return
  }

  submitting.value = true
  
  try {
    await diaryStore.addComment({
      diary_id: props.diaryId,
      content: commentContent.value,
      score: commentScore.value
    })
    
    commentContent.value = ''
    commentScore.value = 5
    
    // 重新加载评论
    comments.value = await diaryStore.loadComments(props.diaryId)
    
    alert('评论成功!')
  } catch (error) {
    alert('评论失败: ' + error.message)
  } finally {
    submitting.value = false
  }
}

function handleClose() {
  emit('update:show', false)
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  padding: 20px;
}

.diary-detail-modal {
  max-width: 700px;
  max-height: 90vh;
  overflow-y: auto;
  width: 100%;
}

.modal {
  background: white;
  padding: 30px;
  border-radius: 12px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
  position: relative;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: start;
  margin-bottom: 16px;
}

.modal-header h2 {
  margin: 0;
  color: var(--text-color);
  flex: 1;
  padding-right: 20px;
}

.btn-close {
  background: transparent;
  border: none;
  font-size: 24px;
  color: #9ca3af;
  cursor: pointer;
  padding: 0;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: all 0.2s;
  flex-shrink: 0;
}

.btn-close:hover {
  background: #f3f4f6;
  color: #374151;
}

.diary-meta {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
  font-size: 13px;
  color: #6b7280;
  flex-wrap: wrap;
}

.diary-content {
  margin: 20px 0;
  line-height: 1.6;
  white-space: pre-wrap;
  color: #374151;
}

/* 小红书风格图片网格布局 */
.diary-images-grid {
  display: grid;
  gap: 8px;
  margin: 16px 0;
}

/* 单张图片：居中显示 */
.diary-images-grid.single-layout {
  grid-template-columns: 1fr;
}

.image-item {
  position: relative;
  overflow: hidden;
  border-radius: 8px;
  cursor: pointer;
  background: #f3f4f6;
}

.image-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s;
  display: block;
}

.image-item:hover img {
  transform: scale(1.05);
}

/* 1张图：大图显示 */
.image-item.single {
  grid-column: span 3;
  max-height: 400px;
}

.image-item.single img {
  object-fit: contain;
  background: #000;
}

/* 2张图：左右平分 */
.diary-images-grid:has(.image-item.double) {
  grid-template-columns: repeat(2, 1fr);
}

.image-item.double {
  aspect-ratio: 1;
}

/* 4张图：2x2网格 */
.diary-images-grid:has(.image-item.quad) {
  grid-template-columns: repeat(2, 1fr);
}

.image-item.quad {
  aspect-ratio: 1;
}

/* 3张或5+张：标准3列网格 */
.diary-images-grid:has(.image-item.grid) {
  grid-template-columns: repeat(3, 1fr);
}

.image-item.grid {
  aspect-ratio: 1;
}

/* 大图查看器 */
.image-viewer {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.9);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  padding: 20px;
}

.image-viewer img {
  max-width: 90%;
  max-height: 90vh;
  object-fit: contain;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
}

.viewer-close {
  position: absolute;
  top: 20px;
  right: 20px;
  background: rgba(255, 255, 255, 0.2);
  border: none;
  color: white;
  font-size: 32px;
  width: 50px;
  height: 50px;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  backdrop-filter: blur(10px);
}

.viewer-close:hover {
  background: rgba(255, 255, 255, 0.3);
  transform: scale(1.1);
}

hr {
  border: none;
  border-top: 1px solid #e5e7eb;
  margin: 24px 0;
}

h3 {
  margin: 0 0 16px 0;
  font-size: 1.1rem;
  color: #374151;
}

.comments-list {
  max-height: 300px;
  overflow-y: auto;
  margin-bottom: 20px;
}

.empty-message {
  text-align: center;
  color: #9ca3af;
  padding: 20px;
  font-size: 14px;
}

.comment-item {
  background: #f9fafb;
  padding: 12px;
  border-radius: 6px;
  margin-bottom: 10px;
}

.comment-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-size: 13px;
}

.comment-author {
  font-weight: 600;
  color: #374151;
}

.comment-score {
  color: #f59e0b;
}

.comment-content {
  color: #4b5563;
  font-size: 14px;
  line-height: 1.5;
}

.comment-form {
  background: #f9fafb;
  padding: 16px;
  border-radius: 8px;
}

.comment-form label {
  display: block;
  font-weight: 600;
  margin-bottom: 8px;
  color: #374151;
}

.score-input {
  margin-bottom: 12px;
  font-size: 14px;
  color: #374151;
  display: flex;
  align-items: center;
}

.comment-form textarea {
  width: 100%;
  margin-bottom: 10px;
  resize: vertical;
}

.login-hint {
  text-align: center;
  color: #6b7280;
  padding: 16px;
  background: #f9fafb;
  border-radius: 6px;
  font-size: 14px;
}
</style>
