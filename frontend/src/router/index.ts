import { createRouter, createWebHashHistory } from 'vue-router'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', redirect: '/knowledge' },
    {
      path: '/knowledge',
      name: 'knowledge',
      component: () => import('../views/KnowledgeView.vue'),
    },
    {
      path: '/pipeline',
      name: 'pipeline',
      component: () => import('../views/PipelineView.vue'),
    },
    {
      path: '/tasks',
      name: 'tasks',
      component: () => import('../views/TasksView.vue'),
    },
    {
      path: '/providers',
      name: 'providers',
      component: () => import('../views/ProvidersView.vue'),
    },
  ],
})

export default router
