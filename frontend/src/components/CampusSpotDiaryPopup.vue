<template>
  <Transition name="spot-popup">
    <div
      v-if="show"
      ref="popupRef"
      class="spot-diary-popup"
      :style="popupPlacement.style"
    >
      <div class="popup-header">
        <div>
          <h3 class="popup-title">{{ spotName || '景点日记' }}</h3>
          <p class="popup-subtitle">{{ loading ? '正在加载...' : `共 ${diaries.length} 篇社区日记` }}</p>
        </div>
        <button class="popup-close" type="button" @click="$emit('close')">✕</button>
      </div>

      <div v-if="loading" class="popup-loading">
        正在加载该点位的社区日记...
      </div>

      <template v-else-if="hasDiaries">
        <article
          v-if="isSingleDiary"
          class="cover-card cover-card-main cover-card-single"
          role="button"
          tabindex="0"
          @click="openDiary(primaryDiary.id)"
          @keydown.enter.prevent="openDiary(primaryDiary.id)"
          @keydown.space.prevent="openDiary(primaryDiary.id)"
        >
          <img v-if="getCover(primaryDiary)" :src="getCover(primaryDiary)" alt="日记封面" class="cover-image" />
          <div v-else class="cover-placeholder">暂无封面</div>
          <div class="cover-mask">
            <h4>{{ primaryDiary.title }}</h4>
            <p>{{ primaryDiary.user_name }} · 👁️ {{ primaryDiary.view_count || 0 }}</p>
          </div>
        </article>

        <div v-else class="cover-layout">
          <article
            class="cover-card cover-card-main"
            role="button"
            tabindex="0"
            @click="openDiary(primaryDiary.id)"
            @keydown.enter.prevent="openDiary(primaryDiary.id)"
            @keydown.space.prevent="openDiary(primaryDiary.id)"
          >
            <img v-if="getCover(primaryDiary)" :src="getCover(primaryDiary)" alt="日记封面" class="cover-image" />
            <div v-else class="cover-placeholder">暂无封面</div>
            <div class="cover-mask">
              <h4>{{ primaryDiary.title }}</h4>
              <p>{{ primaryDiary.user_name }} · 👁️ {{ primaryDiary.view_count || 0 }}</p>
            </div>
          </article>

          <div class="cover-side-list">
            <article
              v-for="diary in secondaryDiaries"
              :key="diary.id"
              class="cover-card cover-card-side"
              role="button"
              tabindex="0"
              @click="openDiary(diary.id)"
              @keydown.enter.prevent="openDiary(diary.id)"
              @keydown.space.prevent="openDiary(diary.id)"
            >
              <img v-if="getCover(diary)" :src="getCover(diary)" alt="日记封面" class="cover-image" />
              <div v-else class="cover-placeholder">暂无封面</div>
              <div class="cover-mask">
                <h4>{{ diary.title }}</h4>
                <p>{{ diary.user_name }} · 👁️ {{ diary.view_count || 0 }}</p>
              </div>
            </article>
          </div>
        </div>
      </template>

      <div v-else class="popup-empty">
        {{ emptyText }}
      </div>
    </div>
  </Transition>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'

const props = defineProps({
  show: Boolean,
  loading: Boolean,
  spotName: {
    type: String,
    default: ''
  },
  diaries: {
    type: Array,
    default: () => []
  },
  emptyText: {
    type: String,
    default: '该点位暂无社区日记'
  },
  anchorX: {
    type: Number,
    default: null
  },
  anchorY: {
    type: Number,
    default: null
  },
  viewportWidth: {
    type: Number,
    default: 0
  },
  viewportHeight: {
    type: Number,
    default: 0
  }
})

const emit = defineEmits(['close', 'open-diary'])
const popupRef = ref(null)
const popupSize = ref({ width: 0, height: 0 })
let popupResizeObserver = null

const hasDiaries = computed(() => Array.isArray(props.diaries) && props.diaries.length > 0)
const isSingleDiary = computed(() => props.diaries.length === 1)
const primaryDiary = computed(() => props.diaries[0] || {})
const secondaryDiaries = computed(() => props.diaries.slice(1))
const popupPlacement = computed(() => {
  const margin = 12
  const gap = 14
  const viewportWidth = Number(props.viewportWidth) || 0
  const viewportHeight = Number(props.viewportHeight) || 0
  const fallbackWidth = Math.max(280, viewportWidth - margin * 2)
  const fallbackHeight = Math.max(220, viewportHeight * 0.42)
  const width = popupSize.value.width || Math.min(680, fallbackWidth)
  const height = popupSize.value.height || Math.min(420, fallbackHeight)
  const hasAnchor = Number.isFinite(props.anchorX) && Number.isFinite(props.anchorY) && viewportWidth > 0 && viewportHeight > 0

  if (!hasAnchor) {
    return {
      style: {
        left: `${margin}px`,
        top: `${margin}px`,
        '--popup-arrow-x': '50%',
        '--popup-origin-x': '50%',
        '--popup-origin-y': '100%',
        '--popup-enter-offset': '16px'
      }
    }
  }

  const anchorX = props.anchorX
  const anchorY = props.anchorY
  const left = anchorX - width / 2
  const top = anchorY - gap - height

  return {
    style: {
      left: `${left}px`,
      top: `${top}px`,
      '--popup-arrow-x': '50%',
      '--popup-origin-x': '50%',
      '--popup-origin-y': `${height}px`,
      '--popup-enter-offset': '16px'
    }
  }
})

function getCover(diary) {
  if (!diary || !Array.isArray(diary.media_files) || diary.media_files.length === 0) {
    return ''
  }
  return diary.media_files[0] || ''
}

function openDiary(diaryId) {
  emit('open-diary', diaryId)
}

function updatePopupSize() {
  if (!popupRef.value) return

  popupSize.value = {
    width: popupRef.value.offsetWidth,
    height: popupRef.value.offsetHeight
  }
}

watch(popupRef, (element, previousElement) => {
  if (popupResizeObserver && previousElement) {
    popupResizeObserver.unobserve(previousElement)
  }
  if (popupResizeObserver && element) {
    popupResizeObserver.observe(element)
  }
  if (element) {
    nextTick(updatePopupSize)
  }
})

watch(
  () => [props.show, props.loading, props.diaries.length, props.spotName, props.emptyText],
  ([visible]) => {
    if (visible) {
      nextTick(updatePopupSize)
    }
  }
)

onMounted(() => {
  if (typeof ResizeObserver !== 'undefined') {
    popupResizeObserver = new ResizeObserver(() => {
      updatePopupSize()
    })

    if (popupRef.value) {
      popupResizeObserver.observe(popupRef.value)
    }
  }

  if (props.show) {
    nextTick(updatePopupSize)
  }
})

onUnmounted(() => {
  if (popupResizeObserver) {
    popupResizeObserver.disconnect()
    popupResizeObserver = null
  }
})
</script>

<style scoped>
.spot-diary-popup {
  position: absolute;
  z-index: 900;
  width: min(680px, calc(100% - 24px));
  max-height: calc(100% - 24px);
  background: rgba(255, 255, 255, 0.93);
  backdrop-filter: blur(10px);
  border-radius: 14px;
  box-shadow: 0 18px 38px rgba(15, 39, 70, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.6);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 12px;
  transform-origin: var(--popup-origin-x, 50%) var(--popup-origin-y, 100%);
  will-change: transform, opacity, filter;
}

.spot-diary-popup::after {
  content: '';
  position: absolute;
  width: 12px;
  height: 12px;
  left: var(--popup-arrow-x, 50%);
  bottom: -6px;
  transform: translateX(-50%) rotate(45deg);
  background: rgba(255, 255, 255, 0.93);
  border-right: 1px solid rgba(255, 255, 255, 0.6);
  border-bottom: 1px solid rgba(255, 255, 255, 0.6);
}

.popup-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.popup-title {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: #12365e;
}

.popup-subtitle {
  margin: 4px 0 0;
  font-size: 12px;
  color: #537497;
}

.popup-close {
  border: none;
  border-radius: 999px;
  width: 30px;
  height: 30px;
  background: rgba(226, 237, 251, 0.9);
  color: #315f90;
  font-size: 16px;
  cursor: pointer;
}

.popup-close:hover {
  background: #dbeafe;
}

.popup-loading {
  border-radius: 10px;
  background: #f3f8ff;
  color: #45698f;
  font-size: 13px;
  padding: 14px;
  text-align: center;
}

.popup-empty {
  border-radius: 10px;
  background: #f3f8ff;
  color: #45698f;
  font-size: 13px;
  padding: 14px;
  text-align: center;
}

.cover-layout {
  display: grid;
  grid-template-columns: 1.6fr 1fr;
  gap: 10px;
  min-height: 0;
}

.cover-side-list {
  display: grid;
  grid-auto-rows: 110px;
  gap: 10px;
  overflow-y: auto;
  padding-right: 2px;
}

.cover-card {
  position: relative;
  border-radius: 10px;
  overflow: hidden;
  border: none;
  padding: 0;
  background: #dbe8f7;
  cursor: pointer;
}

.cover-card:hover {
  transform: translateY(-1px);
}

.cover-card-main {
  min-height: 248px;
}

.cover-card-single {
  min-height: 320px;
}

.cover-card-side {
  min-height: 110px;
}

.cover-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.cover-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: #4f6b8a;
  background: linear-gradient(135deg, #dcecff, #c6dbf4);
}

.cover-mask {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 10px;
  background: linear-gradient(180deg, rgba(6, 26, 52, 0) 0%, rgba(6, 26, 52, 0.82) 90%);
  color: #fff;
}

.cover-mask h4 {
  margin: 0 0 4px;
  font-size: 14px;
  line-height: 1.3;
}

.cover-mask p {
  margin: 0;
  font-size: 12px;
  opacity: 0.92;
}

.spot-popup-enter-active,
.spot-popup-leave-active {
  transform-origin: inherit;
}

.spot-popup-enter-active {
  transition:
    transform 0.32s cubic-bezier(0.16, 1, 0.3, 1),
    opacity 0.26s cubic-bezier(0.2, 0.8, 0.2, 1),
    filter 0.24s cubic-bezier(0.2, 0.8, 0.2, 1);
}

.spot-popup-leave-active {
  transition:
    transform 0.22s cubic-bezier(0.4, 0, 1, 1),
    opacity 0.18s ease,
    filter 0.16s ease;
  pointer-events: none;
}

.spot-popup-enter-from,
.spot-popup-leave-to {
  opacity: 0;
  transform: translate3d(0, var(--popup-enter-offset, 16px), 0) scale(0.86);
  filter: blur(2px);
}

@media (max-width: 960px) {
  .spot-diary-popup {
    width: min(560px, calc(100% - 16px));
  }

  .cover-layout {
    grid-template-columns: 1fr;
  }

  .cover-card-main {
    min-height: 220px;
  }

  .cover-side-list {
    grid-auto-rows: 100px;
    max-height: 220px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .spot-popup-enter-active,
  .spot-popup-leave-active {
    transition: opacity 0.15s ease;
  }

  .spot-popup-enter-from,
  .spot-popup-leave-to {
    transform: none;
    filter: none;
  }
}
</style>
