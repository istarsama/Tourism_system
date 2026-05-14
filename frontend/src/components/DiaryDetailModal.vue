<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="show && diary" class="modal-overlay" @click="handleClose">
        <div class="diary-detail-modal" @click.stop>
          <button type="button" class="btn-close" @click="handleClose">✕</button>

          <div class="detail-layout">
            <section class="media-panel">
              <div class="media-stage" @wheel.prevent="handleMediaWheel">
                <Transition :name="mediaTransitionName">
                  <img
                    v-if="currentMediaUrl"
                    :key="currentMediaKey"
                    :src="currentMediaUrl"
                    alt="日记图片"
                    class="media-image"
                  />
                  <div v-else key="media-empty" class="media-empty">
                    <p>暂无图片</p>
                  </div>
                </Transition>

                <button
                  v-if="hasMultipleMedia"
                  type="button"
                  class="media-nav media-nav-prev"
                  @click="prevMedia"
                >
                  ‹
                </button>
                <button
                  v-if="hasMultipleMedia"
                  type="button"
                  class="media-nav media-nav-next"
                  @click="nextMedia"
                >
                  ›
                </button>

                <div v-if="mediaCount > 0" class="media-counter">
                  {{ currentMediaIndex + 1 }} / {{ mediaCount }}
                </div>
              </div>

              <div v-if="hasMultipleMedia" class="media-dots">
                <button
                  v-for="(_, index) in mediaFiles"
                  :key="index"
                  type="button"
                  class="dot"
                  :class="{ active: index === currentMediaIndex }"
                  @click="selectMedia(index)"
                ></button>
              </div>
            </section>

            <section class="content-panel">
              <div class="post-main">
                <div class="author-row">
                  <div class="author-avatar">{{ authorInitial }}</div>
                  <div class="author-meta">
                    <p class="author-name">{{ diary.user_name }}</p>
                    <p class="post-time">{{ formattedCreatedAt }}</p>
                  </div>
                </div>

                <h2 class="post-title">{{ diary.title }}</h2>

                <div class="post-stats">
                  <span class="meta-chip">⭐ {{ diary.score?.toFixed(1) || 'N/A' }}</span>
                  <span class="meta-chip">👁️ {{ diary.view_count || 0 }}</span>
                </div>

                <div class="post-body">
                  {{ diary.content }}
                </div>
              </div>

              <div class="comment-zone">
                <h3>评论区 ({{ comments.length }})</h3>

                <div class="comments-list">
                  <div v-if="comments.length === 0" class="empty-message">
                    暂无评论
                  </div>

                  <div
                    v-else
                    v-for="(comment, index) in comments"
                    :key="comment.id ?? `${comment.user_name}-${comment.created_at}-${index}`"
                    class="comment-item"
                  >
                    <div class="comment-header">
                      <span class="comment-author">{{ comment.user_name }}</span>
                      <span class="comment-score">⭐ {{ comment.score }}</span>
                    </div>
                    <div class="comment-content">{{ comment.content }}</div>
                  </div>
                </div>

                <div v-if="authStore.isAuthenticated" class="comment-form">
                  <label>发表评论</label>
                  <div class="score-input">
                    打分:
                    <input
                      v-model.number="commentScore"
                      type="number"
                      min="1"
                      max="5"
                    />
                    / 5
                  </div>
                  <textarea
                    v-model="commentContent"
                    rows="3"
                    placeholder="写下你的评论..."
                  ></textarea>
                  <button
                    type="button"
                    class="btn-submit"
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
            </section>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
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
const currentMediaIndex = ref(0)
const mediaSlideDirection = ref('next')
let lastWheelSwitchAt = 0
const MEDIA_WHEEL_SWITCH_INTERVAL_MS = 220

const mediaFiles = computed(() => {
  const files = diary.value?.media_files
  return Array.isArray(files) ? files : []
})
const mediaCount = computed(() => mediaFiles.value.length)
const hasMultipleMedia = computed(() => mediaCount.value > 1)
const currentMediaUrl = computed(() => mediaFiles.value[currentMediaIndex.value] || '')
const currentMediaKey = computed(() =>
  currentMediaUrl.value ? `${props.diaryId || 'diary'}-${currentMediaIndex.value}` : 'media-empty'
)
const mediaTransitionName = computed(() =>
  mediaSlideDirection.value === 'prev' ? 'media-slide-right' : 'media-slide-left'
)
const authorInitial = computed(() => {
  const name = diary.value?.user_name?.trim()
  return name ? name[0].toUpperCase() : '游'
})
const formattedCreatedAt = computed(() => formatDate(diary.value?.created_at))

watch(
  () => props.show,
  async (newVal) => {
    if (newVal && props.diaryId) {
      currentMediaIndex.value = 0
      await loadDiaryDetail()
    }
  }
)

watch(
  () => props.diaryId,
  async (newDiaryId, oldDiaryId) => {
    if (!props.show || !newDiaryId || newDiaryId === oldDiaryId) return
    currentMediaIndex.value = 0
    await loadDiaryDetail()
  }
)

async function loadDiaryDetail() {
  try {
    diary.value = await diaryStore.loadDiary(props.diaryId)
    comments.value = await diaryStore.loadComments(props.diaryId)
    currentMediaIndex.value = 0
  } catch (error) {
    alert('加载日记失败: ' + error.message)
    handleClose()
  }
}

function formatDate(value) {
  if (!value) return '未知时间'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function prevMedia() {
  if (mediaCount.value < 2) return
  mediaSlideDirection.value = 'prev'
  currentMediaIndex.value = (currentMediaIndex.value - 1 + mediaCount.value) % mediaCount.value
}

function nextMedia() {
  if (mediaCount.value < 2) return
  mediaSlideDirection.value = 'next'
  currentMediaIndex.value = (currentMediaIndex.value + 1) % mediaCount.value
}

function selectMedia(index) {
  if (index < 0 || index >= mediaCount.value) return
  if (index === currentMediaIndex.value) return
  mediaSlideDirection.value = index > currentMediaIndex.value ? 'next' : 'prev'
  currentMediaIndex.value = index
}

function handleMediaWheel(event) {
  if (mediaCount.value < 2) return

  const dominantDelta =
    Math.abs(event.deltaY) >= Math.abs(event.deltaX) ? event.deltaY : event.deltaX
  if (!Number.isFinite(dominantDelta) || Math.abs(dominantDelta) < 4) return

  const now = Date.now()
  if (now - lastWheelSwitchAt < MEDIA_WHEEL_SWITCH_INTERVAL_MS) return
  lastWheelSwitchAt = now

  if (dominantDelta > 0) {
    nextMedia()
    return
  }
  prevMedia()
}

async function handleSubmitComment() {
  if (!commentContent.value.trim()) {
    alert('请输入评论内容')
    return
  }
  if (!Number.isFinite(commentScore.value) || commentScore.value < 1 || commentScore.value > 5) {
    alert('评分需在 1 到 5 之间')
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
  inset: 0;
  background: rgba(6, 24, 56, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  padding: 20px;
}

.diary-detail-modal {
  position: relative;
  width: min(1200px, 96vw);
  height: min(860px, 92vh);
  border-radius: 16px;
  overflow: hidden;
  background: linear-gradient(180deg, #f5f9ff 0%, #edf4ff 100%);
  box-shadow: 0 22px 56px rgba(0, 45, 98, 0.25);
}

.btn-close {
  position: absolute;
  top: 12px;
  right: 12px;
  width: 34px;
  height: 34px;
  border: none;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.85);
  color: #335b87;
  font-size: 20px;
  cursor: pointer;
  z-index: 10;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.btn-close:hover {
  background: #ffffff;
  color: #003d74;
}

.detail-layout {
  display: grid;
  grid-template-columns: 1.35fr 1fr;
  height: 100%;
}

.media-panel {
  padding: 18px 14px 14px 18px;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.media-stage {
  position: relative;
  flex: 1;
  min-height: 320px;
  border-radius: 14px;
  overflow: hidden;
  background: #d8e7fb;
  border: 1px solid #c7dcfa;
}

.media-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.media-slide-left-enter-active,
.media-slide-left-leave-active,
.media-slide-right-enter-active,
.media-slide-right-leave-active {
  transition: transform 0.28s ease;
  position: absolute;
  inset: 0;
}

.media-slide-left-enter-from,
.media-slide-right-leave-to {
  transform: translateX(100%);
}

.media-slide-left-leave-to,
.media-slide-right-enter-from {
  transform: translateX(-100%);
}

.media-empty {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #4f6f95;
  font-size: 14px;
  letter-spacing: 0.5px;
}

.media-nav {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 999px;
  cursor: pointer;
  background: rgba(255, 255, 255, 0.86);
  color: #244f7f;
  font-size: 24px;
  line-height: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.media-nav:hover {
  background: #ffffff;
  color: #003d74;
}

.media-nav-prev {
  left: 12px;
}

.media-nav-next {
  right: 12px;
}

.media-counter {
  position: absolute;
  right: 12px;
  top: 12px;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(6, 32, 72, 0.62);
  color: #ffffff;
  font-size: 12px;
  font-weight: 600;
}

.media-dots {
  display: flex;
  justify-content: center;
  gap: 8px;
}

.dot {
  width: 8px;
  height: 8px;
  border: none;
  border-radius: 999px;
  background: #98b7df;
  cursor: pointer;
  transition: all 0.2s;
}

.dot.active {
  width: 20px;
  background: #003d74;
}

.content-panel {
  background: #ffffff;
  border-left: 1px solid #d7e4f7;
  padding: 18px 18px 16px;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.post-main {
  min-height: 0;
  overflow-y: auto;
  padding-right: 4px;
}

.author-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.author-avatar {
  width: 38px;
  height: 38px;
  border-radius: 999px;
  background: linear-gradient(135deg, #2b6aaa, #003d74);
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 16px;
}

.author-meta {
  min-width: 0;
}

.author-name {
  margin: 0;
  color: #123d67;
  font-size: 15px;
  font-weight: 700;
}

.post-time {
  margin: 2px 0 0;
  color: #6f89a8;
  font-size: 12px;
}

.post-title {
  margin: 0 0 10px;
  color: #0f365f;
  font-size: 24px;
  line-height: 1.3;
}

.post-stats {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.meta-chip {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  background: #edf4ff;
  color: #315a87;
  font-size: 12px;
  font-weight: 600;
}

.post-body {
  color: #2b4664;
  font-size: 15px;
  line-height: 1.75;
  white-space: pre-wrap;
}

.comment-zone {
  border: 1px solid #dce8f9;
  border-radius: 12px;
  background: #f7faff;
  padding: 12px;
}

.comment-zone h3 {
  margin: 0 0 10px;
  color: #144a7c;
  font-size: 15px;
  font-weight: 700;
}

.comments-list {
  max-height: 220px;
  overflow-y: auto;
  margin-bottom: 10px;
}

.empty-message {
  text-align: center;
  color: #85a0bf;
  padding: 16px;
  font-size: 13px;
}

.comment-item {
  background: #ffffff;
  border: 1px solid #e0ebfa;
  padding: 10px;
  border-radius: 8px;
  margin-bottom: 8px;
}

.comment-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.comment-author {
  color: #1e4973;
  font-size: 13px;
  font-weight: 600;
}

.comment-score {
  color: #3c6a9a;
  font-size: 12px;
  font-weight: 600;
}

.comment-content {
  color: #445d79;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
}

.comment-form label {
  display: block;
  margin-bottom: 8px;
  color: #1f4c79;
  font-size: 13px;
  font-weight: 600;
}

.score-input {
  margin-bottom: 8px;
  color: #35597d;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.score-input input {
  width: 64px;
  height: 32px;
  border: 1px solid #c8daef;
  border-radius: 8px;
  padding: 0 8px;
}

.comment-form textarea {
  width: 100%;
  border: 1px solid #c8daef;
  border-radius: 8px;
  resize: vertical;
  padding: 8px 10px;
  margin-bottom: 8px;
  min-height: 78px;
}

.comment-form textarea:focus,
.score-input input:focus {
  outline: none;
  border-color: #4f84bb;
  box-shadow: 0 0 0 3px rgba(79, 132, 187, 0.15);
}

.btn-submit {
  border: none;
  border-radius: 8px;
  padding: 8px 14px;
  background: linear-gradient(135deg, #2f6da8, #003d74);
  color: #ffffff;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-submit:hover:not(:disabled) {
  transform: translateY(-1px);
}

.btn-submit:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.login-hint {
  border-radius: 8px;
  background: #eef5ff;
  border: 1px dashed #c8daef;
  color: #58789e;
  font-size: 13px;
  text-align: center;
  padding: 10px;
}

@media (max-width: 1100px) {
  .diary-detail-modal {
    width: min(920px, 96vw);
    height: min(920px, 94vh);
  }

  .detail-layout {
    grid-template-columns: 1fr;
    grid-template-rows: minmax(280px, 42vh) 1fr;
  }

  .content-panel {
    border-left: none;
    border-top: 1px solid #d7e4f7;
  }
}

@media (max-width: 640px) {
  .modal-overlay {
    padding: 10px;
  }

  .diary-detail-modal {
    border-radius: 12px;
  }

  .media-panel {
    padding: 12px;
  }

  .content-panel {
    padding: 14px 12px 12px;
  }

  .post-title {
    font-size: 19px;
  }

  .comments-list {
    max-height: 170px;
  }
}
</style>
