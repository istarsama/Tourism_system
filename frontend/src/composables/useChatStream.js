import { ref, nextTick, reactive, toRefs } from 'vue'

/**
 * 高性能流式聊天 Composable
 * 实现逐字渲染、缓冲队列、智能滚动
 * 用于优化AI聊天界面的流式文本显示，提升用户体验
 */
export function useChatStream() {
  // 是否正在流式输出
  const isStreaming = ref(false)

  // 字符缓冲区队列，用于平滑渲染
  const streamBuffer = ref([])

  /**
   * 处理真实的流式数据（从ReadableStream）
   * @param {ReadableStream} stream - 后端返回的流对象
   * @param {Object} messageObj - 消息对象（响应式），需要有text和isStreaming属性
   * @param {Function} onUpdate - 每次文本更新时的回调函数，用于触发滚动等副作用
   */
  async function processStream(stream, messageObj, onUpdate) {
    const reader = stream.getReader()
    const decoder = new TextDecoder()
    isStreaming.value = true

    try {
      while (true) {
        const { done, value } = await reader.read()

        if (done) break

        // 解码二进制数据块为字符串
        const chunk = decoder.decode(value, { stream: true })

        // 将大块数据拆分为单个字符，放入缓冲区
        // 这样可以控制渲染速度，避免一次性渲染大量文本造成卡顿
        for (const char of chunk) {
          streamBuffer.value.push(char)
        }

        // 给 Vue 一个渲染周期，避免阻塞UI
        await nextTick()

        // 开始消费缓冲区，匀速渲染字符
        consumeBuffer(messageObj, onUpdate)
      }

      // 流结束，清空剩余缓冲区
      await flushBuffer(messageObj, onUpdate)

    } catch (error) {
      console.error('流式读取错误:', error)
      throw error
    } finally {
      reader.releaseLock()
      isStreaming.value = false
    }
  }

  /**
   * 消费缓冲区 - 匀速渲染字符
   * 使用 requestAnimationFrame 同步屏幕刷新率，确保流畅动画
   * @param {Object} messageObj - 消息对象
   * @param {Function} onUpdate - 更新回调
   */
  function consumeBuffer(messageObj, onUpdate) {
    if (streamBuffer.value.length === 0) return

    const renderBatch = () => {
      // 每帧最多渲染3个字符（60fps，每帧约16ms）
      // 平衡渲染速度和性能
      const batchSize = Math.min(3, streamBuffer.value.length)

      for (let i = 0; i < batchSize; i++) {
        const char = streamBuffer.value.shift()
        if (char) {
          // 强制触发Vue响应式更新
          messageObj.text = messageObj.text + char
        }
      }

      // 触发更新回调（通常用于滚动到底部）
      if (onUpdate) {
        onUpdate()
      }

      // 如果缓冲区还有数据，继续下一帧渲染
      if (streamBuffer.value.length > 0) {
        requestAnimationFrame(renderBatch)
      }
    }

    requestAnimationFrame(renderBatch)
  }

  /**
   * 清空缓冲区剩余字符
   * @param {Object} messageObj - 消息对象
   * @param {Function} onUpdate - 更新回调
   */
  async function flushBuffer(messageObj, onUpdate) {
    while (streamBuffer.value.length > 0) {
      const char = streamBuffer.value.shift()
      // 强制触发响应式更新
      messageObj.text = messageObj.text + char

      // 每10个字符给Vue一次渲染机会
      if (streamBuffer.value.length % 10 === 0) {
        await nextTick()
        if (onUpdate) onUpdate()
      }
    }

    // 最后一次更新
    await nextTick()
    if (onUpdate) onUpdate()
  }

  /**
   * 模拟流式输出（用于非流式API）
   * 将完整文本拆分逐字显示，模拟流式效果
   * @param {String} text - 完整的回复文本
   * @param {Object} messageObj - 消息对象
   * @param {Function} onUpdate - 更新回调
   */
  async function simulateStream(text, messageObj, onUpdate) {
    messageObj.text = ''
    messageObj.isStreaming = true
    isStreaming.value = true

    const chars = text.split('')

    for (let i = 0; i < chars.length; i++) {
      messageObj.text += chars[i]

      // 每5个字符渲染一次，平衡速度和性能
      if (i % 5 === 0) {
        await nextTick()
        if (onUpdate) onUpdate()

        // 使用requestAnimationFrame同步刷新率
        await new Promise(resolve => {
          requestAnimationFrame(() => {
            setTimeout(resolve, 16) // ~60fps
          })
        })
      }
    }

    messageObj.isStreaming = false
    isStreaming.value = false

    await nextTick()
    if (onUpdate) onUpdate()
  }

  return {
    isStreaming,     // 是否正在流式输出
    processStream,   // 处理真实流
    simulateStream,  // 模拟流式输出
    streamBuffer     // 缓冲区（调试用）
  }
}

/**
 * 智能滚动 Composable
 * 检测用户是否在查看历史记录，避免自动滚动打断用户阅读
 * @param {Ref} containerRef - 滚动容器的ref
 */
export function useSmartScroll(containerRef) {
  // 用户是否正在查看历史记录
  const isUserScrolling = ref(false)

  // 是否启用自动滚动
  const autoScrollEnabled = ref(true)

  let scrollTimeout = null

  /**
   * 处理滚动事件，检测用户意图
   */
  function handleScroll() {
    const container = containerRef.value
    if (!container) return

    const { scrollTop, scrollHeight, clientHeight } = container
    const distanceFromBottom = scrollHeight - scrollTop - clientHeight

    // 如果距离底部超过100px，认为用户在查看历史记录
    isUserScrolling.value = distanceFromBottom > 100
    autoScrollEnabled.value = distanceFromBottom < 100

    // 清除之前的定时器
    if (scrollTimeout) {
      clearTimeout(scrollTimeout)
    }

    // 用户停止滚动1秒后，重新启用自动滚动
    scrollTimeout = setTimeout(() => {
      isUserScrolling.value = false
      autoScrollEnabled.value = true
    }, 1000)
  }

  /**
   * 平滑滚动到底部
   * @param {Boolean} force - 是否强制滚动（忽略用户查看历史）
   */
  async function scrollToBottom(force = false) {
    // 如果用户正在查看历史，且非强制滚动，则不滚动
    if (isUserScrolling.value && !force) {
      return
    }

    await nextTick()

    const container = containerRef.value
    if (!container) return

    container.scrollTo({
      top: container.scrollHeight,
      behavior: 'smooth'
    })
  }

  /**
   * 立即滚动到底部（无动画）
   */
  function scrollToBottomInstant() {
    const container = containerRef.value
    if (!container) return

    container.scrollTop = container.scrollHeight
  }

  return {
    isUserScrolling,      // 用户是否在查看历史
    autoScrollEnabled,    // 是否启用自动滚动
    handleScroll,         // 滚动事件处理
    scrollToBottom,       // 平滑滚动到底部
    scrollToBottomInstant // 立即滚动到底部
  }
}
