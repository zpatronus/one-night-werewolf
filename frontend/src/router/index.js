import { createRouter, createWebHistory } from 'vue-router'
import { base } from '../store'

const routes = [
  { path: '/', name: 'home', component: () => import('../views/HomeView.vue') },
  { path: '/createroom', name: 'create', component: () => import('../views/CreateRoomView.vue') },
  { path: '/joinroom', name: 'join', component: () => import('../views/JoinRoomView.vue') },
  { path: '/waitingroom', name: 'waiting', component: () => import('../views/WaitingRoomView.vue') },
  { path: '/ops', name: 'ops', component: () => import('../views/OperationView.vue') },
  { path: '/showinfo', name: 'showinfo', component: () => import('../views/ShowInfoView.vue'),
    beforeEnter: (_to, from) => from.path === '/ops' ? true : '/discussion' },
  { path: '/discussion', name: 'discussion', component: () => import('../views/DiscussionView.vue') },
  { path: '/reveal', redirect: '/discussion' },
  { path: '/result', name: 'result', component: () => import('../views/ResultView.vue') },
]

export default createRouter({
  history: createWebHistory(base),
  routes,
})