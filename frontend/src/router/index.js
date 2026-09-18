import { createRouter, createWebHistory } from 'vue-router'
import { base } from '../store'

const routes = [
  { path: '/', name: 'home', component: () => import('../views/HomeView.vue') },
  { path: '/room', name: 'room', component: () => import('../views/RoomEntryView.vue') },
  { path: '/createroom', name: 'create', redirect: to => ({ path: '/room', query: to.query }) },
  { path: '/joinroom', name: 'join', redirect: to => ({ path: '/room', query: to.query }) },
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