<template>
  <div 
    class="chat-panel" 
    :class="{ 
      collapsed: !isExpanded, 
      focused: isInputFocused, 
      dragging: isDragging,
      'transition-none': isDragging 
    }"
    :style="panelStyle"
  >
    <Transition name="tip-fade">
      <div v-if="!isExpanded && showExpandTip" class="chat-tip">
        点击圆球即可使用 AI 助手
      </div>
    </Transition>

    <!-- AI 状态标识符 -->
    <div 
      class="chat-header"
      @mousedown="handleDragStart"
      @click="handleHeaderClick"
      :class="{ 'chat-header-collapsed': !isExpanded }"
    >
      <div v-if="isExpanded" class="header-content">
        <button
          class="collapse-orb-btn"
          title="收起 AI 助手"
          @mousedown.stop
          @click.stop="collapsePanel"
        >
          🤖
        </button>
        <div class="ai-status-indicator" :class="{ thinking: isThinking }">
          <div class="status-dot"></div>
        </div>
        <h4>AI 导游助手</h4>
        <span class="status-text">{{ isThinking ? '思考中...' : '在线' }}</span>
      </div>
    </div>

    <!-- 思考状态骨架屏 -->
    <Transition name="skeleton-fade">
      <div v-if="isThinking && isExpanded" class="thinking-overlay">
        <div class="skeleton-lines">
          <div class="skeleton-line" v-for="i in 3" :key="i" :style="{ width: `${60 + i * 10}%` }"></div>
        </div>
      </div>
    </Transition>

    <!-- 对话消息区域 -->
    <div 
      v-if="isExpanded" 
      class="chat-messages" 
      ref="messagesRef"
      @scroll="handleScroll"
    >
      <TransitionGroup name="message-slide" tag="div" class="messages-container">
        <div
          v-for="msg in messages"
          :key="msg.id"
          class="message-wrapper"
          :class="msg.role"
        >
          <div class="message-bubble" :class="msg.role">
            <div 
              v-if="msg.isStreaming" 
              class="streaming-text"
              v-html="highlightLocations(msg.text)"
            ></div>
            <div 
              v-else
              v-html="highlightLocations(msg.html || msg.text)"
            ></div>
          </div>
        </div>
      </TransitionGroup>
      
      <!-- 用户正在查看历史记录提示 -->
      <Transition name="fade">
        <div v-if="isUserScrolling" class="scroll-hint">
          <button @click="scrollToBottom(true)" class="scroll-to-bottom-btn">
            ↓ 回到底部
          </button>
        </div>
      </Transition>
    </div>

    <!-- 输入区域 -->
    <div v-if="isExpanded" class="chat-input-area">
      <input
        v-model="userInput"
        type="text"
        placeholder="询问校园导航、美食推荐..."
        @keyup.enter="sendMessage"
        @focus="isInputFocused = true"
        @blur="isInputFocused = false"
        :disabled="isSending"
        class="chat-input"
      />
      <button 
        @click="sendMessage" 
        :disabled="isSending || !userInput.trim()"
        class="send-button"
      >
        <span v-if="!isSending">发送</span>
        <span v-else class="loading-dots">
          <span>.</span><span>.</span><span>.</span>
        </span>
      </button>
    </div>
  </div>
</template>


<script setup>
import { ref, reactive, nextTick, watch, computed } from 'vue'
import { api } from '../api'
import { useChatStream, useSmartScroll } from '../composables/useChatStream'

// 状态管理
const isExpanded = ref(false)
const isInputFocused = ref(false)
const isThinking = ref(false)
const isSending = ref(false)
const TIP_STORAGE_KEY = 'chat_panel_tip_seen_v1'
const showExpandTip = ref(localStorage.getItem(TIP_STORAGE_KEY) !== '1')

// 消息数据
let messageId = 0
const messages = ref([
  {
    id: messageId++,
    role: 'ai',
    text: '你好！我是校园AI助手，有什么可以帮你的吗？你可以问我关于旅游日记的问题哦。',
    isStreaming: false
  }
])

const userInput = ref('')
const messagesRef = ref(null)

// 🔥 使用高性能流式渲染 Composable
const { isStreaming, simulateStream } = useChatStream()

// 🔥 使用智能滚动 Composable
const { 
  isUserScrolling, 
  autoScrollEnabled, 
  handleScroll, 
  scrollToBottom,
  scrollToBottomInstant 
} = useSmartScroll(messagesRef)

// 拖拽相关 - 使用 transform 代替 top/left
const isDragging = ref(false)
const dragStartX = ref(0)
const dragStartY = ref(0)
const didDrag = ref(false)
const translateX = ref(0)
const translateY = ref(0)

// 计算样式 - 使用 GPU 加速的 transform
const panelStyle = computed(() => {
  return {
    transform: `translate3d(${translateX.value}px, ${translateY.value}px, 0)`,
    right: '20px',
    bottom: '20px'
  }
})

// 校园地点关键词库
const campusLocations = [
  '图书馆', '食堂', '学一食堂', '学二食堂', '学三食堂',
  '教学楼', '体育馆', '宿舍', '西门', '东门', '南门', '北门',
  '操场', '银杏大道', '樱花园', '人工湖', '行政楼'
]

// 监听消息变化，自动滚动到底部
watch(
  () => messages.value.length,
  () => {
    scrollToBottom()
  }
)

// 拖拽处理 - 使用 transform 优化性能
function handleDragStart(e) {
  isDragging.value = true
  didDrag.value = false
  dragStartX.value = e.clientX
  dragStartY.value = e.clientY

  const handleDragMove = (e) => {
    if (!isDragging.value) return

    const dx = e.clientX - dragStartX.value
    const dy = e.clientY - dragStartY.value
    if (dx !== 0 || dy !== 0) {
      didDrag.value = true
    }

    // 使用 transform 而不是 top/left
    translateX.value += dx
    translateY.value += dy

    dragStartX.value = e.clientX
    dragStartY.value = e.clientY
  }

  const handleDragEnd = () => {
    isDragging.value = false
    document.removeEventListener('mousemove', handleDragMove)
    document.removeEventListener('mouseup', handleDragEnd)
    setTimeout(() => {
      didDrag.value = false
    }, 0)
  }

  document.addEventListener('mousemove', handleDragMove)
  document.addEventListener('mouseup', handleDragEnd)
}

function handleHeaderClick() {
  if (didDrag.value) return
  if (!isExpanded.value) expandPanel()
}

function markTipAsSeen() {
  if (!showExpandTip.value) return
  showExpandTip.value = false
  localStorage.setItem(TIP_STORAGE_KEY, '1')
}

function expandPanel() {
  isExpanded.value = true
  markTipAsSeen()
}

function collapsePanel() {
  isExpanded.value = false
}

// 高亮关键地点
function highlightLocations(text) {
  if (!text) return ''
  
  let result = text
  campusLocations.forEach(location => {
    const regex = new RegExp(`(${location})`, 'g')
    result = result.replace(
      regex, 
      `<span class="location-highlight">
        <svg class="location-icon" viewBox="0 0 24 24" width="14" height="14">
          <path fill="currentColor" d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/>
        </svg>
        $1
      </span>`
    )
  })
  return result
}

// 优化的流式输出效果 - 添加 nextTick 和 requestAnimationFrame
async function simulateStreamingText(text, messageObj) {
  const words = text.split('')
  messageObj.text = ''
  messageObj.isStreaming = true
  
  for (let i = 0; i < words.length; i++) {
    messageObj.text += words[i]
    
    // 每 5 个字符给 Vue 一次渲染机会
    if (i % 5 === 0) {
      await nextTick()
      // 滚动跟随
      await smoothScrollToBottom()
    }
    
    // 使用 requestAnimationFrame 代替 setTimeout，更流畅
    await new Promise(resolve => {
      requestAnimationFrame(() => {
        setTimeout(resolve, 20) // 减少到 20ms，更快
      })
    })
  }
  
  messageObj.isStreaming = false
  await nextTick()
  await smoothScrollToBottom()
}

// 🔥 发送消息 - 使用高性能流式渲染
async function sendMessage() {
  if (!userInput.value.trim() || isSending.value) return

  const userMessage = userInput.value
  
  // 添加用户消息
  messages.value.push({
    id: messageId++,
    role: 'user',
    text: userMessage,
    isStreaming: false
  })

  userInput.value = ''
  isSending.value = true
  isThinking.value = true
  
  // 立即滚动到底部
  await nextTick()
  scrollToBottomInstant()

  try {
    console.log('发送消息到 AI:', userMessage)
    const response = await api.chatWithAI(userMessage)
    console.log('AI 响应:', response)
    
    isThinking.value = false
    
    // 🔥 关键修复：使用 reactive() 包装消息对象，确保深度响应式
    const aiMessage = reactive({
      id: messageId++,
      role: 'ai',
      text: '', // 初始化为空字符串
      html: response.reply_html || null,
      isStreaming: true
    })
    
    messages.value.push(aiMessage)
    
    // 确保消息已添加到 DOM
    await nextTick()
    scrollToBottomInstant()
    
    // 🔥 使用高性能流式渲染
    await simulateStream(response.reply, aiMessage, () => {
      // 每次更新时智能滚动
      scrollToBottom()
    })
    
    // 流式完成
    aiMessage.isStreaming = false
    await nextTick()
    scrollToBottom(true) // 强制滚动到底部
    
  } catch (error) {
    console.error('AI 聊天错误:', error)
    isThinking.value = false
    
    messages.value.push({
      id: messageId++,
      role: 'ai',
      text: `抱歉，我遇到了一些问题：${error.message || '未知错误'}`,
      isStreaming: false
    })
    
    await nextTick()
    scrollToBottom(true)
  } finally {
    isSending.value = false
  }
}
</script>

<style scoped>
/* ========================================
   Glassmorphism 风格的主容器
   ======================================== */
.chat-panel {
  position: fixed;
  width: 380px;
  height: 520px;
  
  /* Glassmorphism 效果 */
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.3);
  box-shadow: 
    0 8px 32px rgba(0, 0, 0, 0.1),
    inset 0 1px 0 rgba(255, 255, 255, 0.5);
  
  display: flex;
  flex-direction: column;
  z-index: 1000;
  overflow: hidden;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  
  /* GPU 加速 */
  will-change: transform;
  transform: translateZ(0);
}

/* 🔥 性能优化：拖拽时移除性能密集的效果 */
.chat-panel.dragging {
  /* 拖拽时移除毛玻璃效果，使用纯色半透明背景 */
  backdrop-filter: none !important;
  -webkit-backdrop-filter: none !important;
  background: rgba(255, 255, 255, 0.95) !important;
  
  /* 移除阴影以提升性能 */
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15) !important;
  
  /* 确保使用 GPU 加速 */
  transform: translateZ(0);
  
  /* 鼠标指针 */
  cursor: move !important;
}

/* 禁止拖拽时的 transition */
.chat-panel.transition-none {
  transition: none !important;
}

/* 输入框聚焦时的外发光效果 */
.chat-panel.focused {
  box-shadow: 
    0 0 0 3px rgba(59, 130, 246, 0.3),
    0 8px 32px rgba(59, 130, 246, 0.2),
    inset 0 1px 0 rgba(255, 255, 255, 0.5);
  border-color: rgba(59, 130, 246, 0.5);
}

/* 折叠状态 */
.chat-panel.collapsed {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: linear-gradient(135deg, #003d74 0%, #0056a3 100%);
  backdrop-filter: none;
  overflow: visible;
  box-shadow: 0 4px 20px rgba(102, 126, 234, 0.5);
}

.collapsed .chat-header {
  width: 100%;
  height: 100%;
  padding: 0;
  display: flex;
  justify-content: center;
  align-items: center;
  background: transparent;
  cursor: pointer;
}

.collapsed .chat-header::after {
  content: '🤖';
  font-size: 32px;
  animation: bounce 2s ease-in-out infinite;
}

@keyframes bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-4px); }
}

.chat-panel.collapsed:hover {
  transform: scale(1.08);
  box-shadow: 0 6px 24px rgba(102, 126, 234, 0.6);
}

/* ========================================
   顶部头部区域
   ======================================== */
.chat-header {
  background: linear-gradient(135deg, #003d74 0%, #0056a3 100%);
  color: white;
  padding: 16px 20px;
  cursor: move;
  user-select: none;
  border-radius: 16px 16px 0 0;
  transition: all 0.3s ease;
}

.chat-header-collapsed {
  cursor: pointer;
}

.header-content {
  display: flex;
  align-items: center;
  gap: 12px;
}

.collapse-orb-btn {
  width: 34px;
  height: 34px;
  border: none;
  border-radius: 50%;
  background: linear-gradient(135deg, #003d74 0%, #0056a3 100%);
  color: #fff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  cursor: pointer;
  box-shadow:
    0 4px 10px rgba(0, 61, 116, 0.45),
    inset 0 1px 0 rgba(255, 255, 255, 0.35);
  border: 1px solid rgba(255, 255, 255, 0.35);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.collapse-orb-btn:hover {
  transform: scale(1.08);
  box-shadow:
    0 6px 14px rgba(0, 86, 163, 0.55),
    inset 0 1px 0 rgba(255, 255, 255, 0.4);
}

.collapse-orb-btn:active {
  transform: scale(0.95);
}

.chat-tip {
  position: absolute;
  right: 78px;
  bottom: 14px;
  white-space: nowrap;
  font-size: 13px;
  font-weight: 600;
  color: #003d74;
  background: rgba(255, 255, 255, 0.96);
  padding: 8px 12px;
  border-radius: 999px;
  border: 1px solid rgba(0, 61, 116, 0.2);
  box-shadow: 0 6px 14px rgba(0, 0, 0, 0.12);
  pointer-events: none;
}

.chat-tip::after {
  content: '';
  position: absolute;
  right: -6px;
  bottom: 18px;
  width: 10px;
  height: 10px;
  background: rgba(255, 255, 255, 0.96);
  border-right: 1px solid rgba(0, 61, 116, 0.2);
  border-top: 1px solid rgba(0, 61, 116, 0.2);
  transform: rotate(45deg);
}

.tip-fade-enter-active,
.tip-fade-leave-active {
  transition: all 0.25s ease;
}

.tip-fade-enter-from,
.tip-fade-leave-to {
  opacity: 0;
  transform: translateX(8px);
}

.chat-header h4 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  flex: 1;
}

.status-text {
  font-size: 12px;
  opacity: 0.9;
  font-weight: 400;
}

/* ========================================
   AI 状态标识符 - 呼吸律动效果
   ======================================== */
.ai-status-indicator {
  width: 10px;
  height: 10px;
  position: relative;
}

.status-dot {
  width: 100%;
  height: 100%;
  background: #10b981;
  border-radius: 50%;
  box-shadow: 0 0 8px rgba(16, 185, 129, 0.6);
  transition: all 0.3s ease;
}

/* 思考状态 - 呼吸动画 */
.ai-status-indicator.thinking .status-dot {
  background: #f59e0b;
  animation: breathe 1.5s ease-in-out infinite;
}

@keyframes breathe {
  0%, 100% {
    transform: scale(1);
    opacity: 1;
    box-shadow: 0 0 8px rgba(245, 158, 11, 0.6);
  }
  50% {
    transform: scale(1.3);
    opacity: 0.7;
    box-shadow: 0 0 16px rgba(245, 158, 11, 0.9);
  }
}

/* ========================================
   思考状态骨架屏
   ======================================== */
.thinking-overlay {
  position: absolute;
  top: 70px;
  left: 20px;
  right: 20px;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(8px);
  border-radius: 12px;
  padding: 16px;
  z-index: 10;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.skeleton-lines {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.skeleton-line {
  height: 12px;
  background: linear-gradient(
    90deg,
    rgba(0, 61, 116, 0.2) 0%,
    rgba(0, 86, 163, 0.5) 50%,
    rgba(0, 61, 116, 0.2) 100%
  );
  background-size: 200% 100%;
  border-radius: 6px;
  animation: shimmer 2s ease-in-out infinite;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* 骨架屏淡入淡出动画 */
.skeleton-fade-enter-active,
.skeleton-fade-leave-active {
  transition: all 0.3s ease;
}

.skeleton-fade-enter-from,
.skeleton-fade-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

/* ========================================
   消息区域
   ======================================== */
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background: rgba(249, 250, 251, 0.5);
  scroll-behavior: smooth;
  position: relative;
  
  /* 🔥 性能优化：减少长对话时的渲染压力 */
  content-visibility: auto;
}

.messages-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
  
  /* 🔥 性能优化：提示浏览器内容会变化 */
  will-change: contents;
}

/* 🔥 用户查看历史记录提示 */
.scroll-hint {
  position: absolute;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 20;
}

.scroll-to-bottom-btn {
  background: linear-gradient(135deg, #003d74 0%, #0056a3 100%);
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 6px;
}

.scroll-to-bottom-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(102, 126, 234, 0.5);
}

.scroll-to-bottom-btn:active {
  transform: translateY(0);
}

/* 淡入淡出动画 */
.fade-enter-active,
.fade-leave-active {
  transition: all 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(10px);
}

/* TransitionGroup 动画 - 从底部滑入 */
.message-slide-enter-active {
  transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.message-slide-enter-from {
  opacity: 0;
  transform: translateY(20px) scale(0.95);
}

.message-slide-enter-to {
  opacity: 1;
  transform: translateY(0) scale(1);
}

/* 消息包装器 */
.message-wrapper {
  display: flex;
  width: 100%;
}

.message-wrapper.user {
  justify-content: flex-end;
}

.message-wrapper.ai {
  justify-content: flex-start;
}

/* 消息气泡 */
.message-bubble {
  padding: 12px 16px;
  border-radius: 16px;
  max-width: 75%;
  word-wrap: break-word;
  line-height: 1.6;
  font-size: 14px;
  position: relative;
}

.message-bubble.user {
  background: linear-gradient(135deg, #003d74 0%, #0056a3 100%);
  color: white;
  border-bottom-right-radius: 4px;
  box-shadow: 0 2px 8px rgba(0, 61, 116, 0.3);
}

.message-bubble.ai {
  background: white;
  border: 1px solid rgba(226, 232, 240, 0.8);
  border-bottom-left-radius: 4px;
  color: #374151;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

/* 流式输出文字动画 */
.streaming-text {
  animation: textAppear 0.3s ease-out;
}

@keyframes textAppear {
  from {
    opacity: 0;
    transform: translateY(-2px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 地点高亮样式 */
.message-bubble :deep(.location-highlight) {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: linear-gradient(135deg, rgba(0, 61, 116, 0.15) 0%, rgba(0, 86, 163, 0.25) 100%);
  color: #003d74;
  padding: 2px 8px;
  border-radius: 6px;
  font-weight: 600;
  transition: all 0.2s ease;
}

.message-bubble :deep(.location-highlight:hover) {
  background: linear-gradient(135deg, rgba(0, 61, 116, 0.25) 0%, rgba(0, 86, 163, 0.35) 100%);
  transform: translateY(-1px);
  box-shadow: 0 2px 6px rgba(0, 61, 116, 0.4);
}

.message-bubble :deep(.location-icon) {
  color: #0056a3;
  vertical-align: middle;
}

/* ========================================
   输入区域
   ======================================== */
.chat-input-area {
  border-top: 1px solid rgba(226, 232, 240, 0.6);
  padding: 16px;
  display: flex;
  gap: 10px;
  background: rgba(255, 255, 255, 0.6);
  backdrop-filter: blur(8px);
}

.chat-input {
  flex: 1;
  padding: 10px 14px;
  border: 2px solid rgba(226, 232, 240, 0.8);
  border-radius: 10px;
  font-size: 14px;
  background: rgba(255, 255, 255, 0.9);
  transition: all 0.3s ease;
  outline: none;
}

.chat-input:focus {
  border-color: #667eea;
  background: white;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.chat-input::placeholder {
  color: #9ca3af;
}

.send-button {
  padding: 10px 20px;
  background: linear-gradient(135deg, #003d74 0%, #0056a3 100%);
  color: white;
  border: none;
  border-radius: 10px;
  cursor: pointer;
  font-weight: 600;
  font-size: 14px;
  transition: all 0.3s ease;
  box-shadow: 0 2px 8px rgba(0, 61, 116, 0.3);
}

.send-button:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 86, 163, 0.5);
}

.send-button:active:not(:disabled) {
  transform: translateY(0);
}

.send-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

/* 加载点动画 */
.loading-dots {
  display: inline-flex;
  gap: 2px;
}

.loading-dots span {
  animation: dotFlash 1.2s infinite;
}

.loading-dots span:nth-child(2) {
  animation-delay: 0.2s;
}

.loading-dots span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes dotFlash {
  0%, 60%, 100% {
    opacity: 1;
  }
  30% {
    opacity: 0.3;
  }
}

/* ========================================
   滚动条美化
   ======================================== */
.chat-messages::-webkit-scrollbar {
  width: 6px;
}

.chat-messages::-webkit-scrollbar-track {
  background: rgba(241, 245, 249, 0.5);
  border-radius: 3px;
}

.chat-messages::-webkit-scrollbar-thumb {
  background: rgba(148, 163, 184, 0.5);
  border-radius: 3px;
  transition: background 0.2s;
}

.chat-messages::-webkit-scrollbar-thumb:hover {
  background: rgba(100, 116, 139, 0.7);
}
</style>
