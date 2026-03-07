<template>
  <div class="relative w-full">
    <!-- 搜索输入框 - Glassmorphism -->
    <div class="relative">
      <div class="absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none">
        <Search :size="18" :class="isFocused ? 'text-bupt-blue' : 'text-gray-400'" class="transition-colors duration-200" />
      </div>
      
      <input
        type="text"
        :value="displayValue"
        :placeholder="placeholder"
        @input="handleInput"
        @focus="handleFocus"
        @blur="handleBlur"
        autocomplete="off"
        class="w-full pl-10 pr-10 py-2.5 bg-white/60 backdrop-blur-sm border border-gray-200/50 rounded-xl 
               text-sm text-gray-900 placeholder-gray-400
               focus:bg-white/80 focus:border-bupt-blue focus:ring-2 focus:ring-bupt-blue/20 focus:outline-none
               transition-all duration-200"
      />
      
      <!-- 加载指示器 -->
      <div v-if="isLoading" class="absolute right-3 top-1/2 -translate-y-1/2">
        <Loader2 :size="16" class="text-bupt-blue animate-spin" />
      </div>
      
      <!-- 清除按钮 -->
      <button 
        v-else-if="displayValue && !isLoading"
        @mousedown.prevent="handleClear"
        class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors active:scale-90"
      >
        <X :size="16" />
      </button>
    </div>

    <!-- 搜索建议列表 - 带动画 -->
    <Transition name="suggestions">
      <div 
        v-if="showSuggestions && suggestions.length > 0"
        class="absolute top-full left-0 right-0 mt-2 bg-white/90 backdrop-blur-md rounded-xl shadow-xl ring-1 ring-black/5 overflow-hidden z-50"
      >
        <TransitionGroup name="suggestion-item" tag="ul" class="max-h-60 overflow-y-auto">
          <li
            v-for="item in suggestions"
            :key="item.id"
            @mousedown.prevent="handleSelect(item)"
            class="px-4 py-3 hover:bg-bupt-blue/5 cursor-pointer transition-colors duration-150 border-b border-gray-100/50 last:border-0 active:scale-[0.98]"
          >
            <div class="flex items-center justify-between gap-2">
              <div class="flex items-center gap-2 flex-1 min-w-0">
                <MapPin :size="14" class="text-bupt-blue flex-shrink-0" />
                <span class="text-sm font-medium text-gray-900 truncate">{{ item.name }}</span>
              </div>
              <span class="text-xs font-semibold text-mint-green bg-mint-green/10 px-2 py-0.5 rounded-full flex-shrink-0">
                {{ item.score }}%
              </span>
            </div>
          </li>
        </TransitionGroup>
      </div>
    </Transition>

    <!-- 骨架屏 - 加载状态 -->
    <Transition name="skeleton">
      <div 
        v-if="showSkeleton"
        class="absolute top-full left-0 right-0 mt-2 bg-white/90 backdrop-blur-md rounded-xl shadow-xl ring-1 ring-black/5 overflow-hidden z-50 p-2"
      >
        <div v-for="i in 3" :key="i" class="px-4 py-3 animate-pulse">
          <div class="flex items-center gap-2">
            <div class="w-4 h-4 bg-gray-200 rounded-full"></div>
            <div class="flex-1 h-4 bg-gray-200 rounded"></div>
            <div class="w-12 h-5 bg-gray-200 rounded-full"></div>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { Search, MapPin, X, Loader2 } from 'lucide-vue-next'
import { useMapStore } from '../stores/map'

const props = defineProps({
  modelValue: String,
  placeholder: String,
  selected: Object
})

const emit = defineEmits(['update:modelValue', 'select'])

const mapStore = useMapStore()
const suggestions = ref([])
const showSuggestions = ref(false)
const isFocused = ref(false)
const isLoading = ref(false)
const showSkeleton = ref(false)

const displayValue = computed(() => {
  return props.selected ? props.selected.name : props.modelValue
})

let searchTimeout = null
let skeletonTimeout = null

function handleInput(e) {
  const value = e.target.value
  emit('update:modelValue', value)
  
  clearTimeout(searchTimeout)
  clearTimeout(skeletonTimeout)
  
  if (!value || value.length < 2) {
    suggestions.value = []
    showSuggestions.value = false
    showSkeleton.value = false
    isLoading.value = false
    return
  }
  
  // 显示骨架屏（延迟 200ms，避免闪烁）
  skeletonTimeout = setTimeout(() => {
    showSkeleton.value = true
  }, 200)
  
  isLoading.value = true
  
  // 防抖搜索（300ms）
  searchTimeout = setTimeout(async () => {
    try {
      const results = await mapStore.searchSpots(value)
      showSkeleton.value = false
      suggestions.value = results
      showSuggestions.value = results.length > 0
    } catch (error) {
      console.error('搜索失败:', error)
    } finally {
      isLoading.value = false
    }
  }, 300)
}

function handleFocus() {
  isFocused.value = true
}

function handleBlur() {
  setTimeout(() => {
    isFocused.value = false
    showSuggestions.value = false
    showSkeleton.value = false
  }, 200)
}

function handleSelect(item) {
  emit('select', item)
  showSuggestions.value = false
  showSkeleton.value = false
}

function handleClear() {
  emit('update:modelValue', '')
  emit('select', null)
  suggestions.value = []
  showSuggestions.value = false
}
</script>

<style scoped>
/* 北邮蓝色系 */
.text-bupt-blue {
  color: #003d74;
}

.border-bupt-blue {
  border-color: #003d74;
}

.ring-bupt-blue\/20 {
  --tw-ring-color: rgba(0, 61, 116, 0.2);
}

.bg-bupt-blue\/5 {
  background-color: rgba(0, 61, 116, 0.05);
}

.text-mint-green {
  color: #10b981;
}

.bg-mint-green\/10 {
  background-color: rgba(16, 185, 129, 0.1);
}

/* 建议列表动画 */
.suggestions-enter-active,
.suggestions-leave-active {
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.suggestions-enter-from {
  opacity: 0;
  transform: translateY(-10px) scale(0.95);
}

.suggestions-leave-to {
  opacity: 0;
  transform: translateY(-5px);
}

/* 建议项动画 */
.suggestion-item-enter-active {
  transition: all 0.2s ease;
}

.suggestion-item-enter-from {
  opacity: 0;
  transform: translateX(-10px);
}

/* 骨架屏动画 */
.skeleton-enter-active,
.skeleton-leave-active {
  transition: all 0.2s ease;
}

.skeleton-enter-from,
.skeleton-leave-to {
  opacity: 0;
  transform: scale(0.95);
}
</style>
