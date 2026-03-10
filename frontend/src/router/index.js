import { createRouter, createWebHashHistory } from 'vue-router'
import { h } from 'vue'

const RouteStateView = {
  name: 'RouteStateView',
  render: () => h('div')
}

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    {
      path: '/',
      redirect: '/nav'
    },
    {
      path: '/nav',
      name: 'Navigation',
      component: RouteStateView,
      meta: {
        title: '导航'
      }
    },
    {
      path: '/diary',
      name: 'Diary',
      component: RouteStateView,
      meta: {
        title: '社区日记'
      }
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/nav'
    }
  ],
  scrollBehavior() {
    return { top: 0 }
  }
})

router.beforeEach((to, _from, next) => {
  if (to.meta.title) {
    document.title = `${to.meta.title} - 校园导游`
  }
  next()
})

export default router
