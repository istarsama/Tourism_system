/**
 * useRouteQuery Composable
 * 
 * 用于在组件中方便地读取和监听 URL 查询参数
 * 
 * 使用示例：
 * const lat = useRouteQuery('lat', '39.9609') // 默认值为北邮纬度
 * const lng = useRouteQuery('lng', '116.3587')
 * 
 * 当 URL 参数变化时，响应式更新组件
 */

import { computed } from 'vue'
import { useRoute } from 'vue-router'

/**
 * 获取并监听路由查询参数
 * @param {string} key - 查询参数名称
 * @param {string} defaultValue - 默认值
 * @returns {import('vue').ComputedRef<string>} 响应式查询参数值
 */
export function useRouteQuery(key, defaultValue = '') {
  const route = useRoute()
  
  return computed(() => {
    const value = route.query[key]
    return value !== undefined ? value : defaultValue
  })
}

/**
 * 获取数字类型的查询参数
 * @param {string} key - 查询参数名称
 * @param {number} defaultValue - 默认值
 * @returns {import('vue').ComputedRef<number>} 响应式数字参数值
 */
export function useRouteQueryNumber(key, defaultValue = 0) {
  const route = useRoute()
  
  return computed(() => {
    const value = route.query[key]
    if (value === undefined || value === null) return defaultValue
    const num = Number(value)
    return isNaN(num) ? defaultValue : num
  })
}
