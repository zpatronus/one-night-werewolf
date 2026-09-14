import { createRouter, createWebHistory } from 'vue-router'
import { base } from '../store'

const routes = [
  { path: '/', name: 'home', component: () => import('../views/HomeView.vue') },
  { path: '/createroom', name: 'create', component: () => import('../views/CreateRoomView.vue') },
  { path: '/joinroom', name: 'join', component: () => import('../views/JoinRoomView.vue') },
  { path: '/waitingroom', name: 'waiting', component: () => import('../views/WaitingRoomView.vue') },
  { path: '/ops', name: 'ops', component: () => import('../views/OperationView.vue') },
  { path: '/reveal', name: 'reveal', component: () => import('../views/RevealView.vue') },
  { path: '/result', name: 'result', component: () => import('../views/ResultView.vue') },
]

export default createRouter({
  history: createWebHistory(base),
  routes,
})