import { onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { post } from './api'
import { creds } from './store'

// One polling loop for every in-room phase view. POSTs /room_state every 2s
// (credentials in body) and, when ``phase`` changes, routes to the right view.
// Also exposes the raw latest snapshot for the view to render.
const PHASE_ROUTE = { waiting: '/waitingroom', op: '/ops', reveal: '/reveal', result: '/result' }
const INTERVAL = 2000

export function useRoomState(onState = null) {
  const router = useRouter()
  const state = ref(null)
  const error = ref(null)
  let timer = null

  async function poll() {
    if (!creds().roomid) return
    const res = await post('room_state', creds())
    if (!res || res.error) {
      error.value = (res && res.error) || 'network_error'
      return
    }
    error.value = null
    state.value = res
    if (onState) onState(res)
    const target = PHASE_ROUTE[res.phase]
    if (target && router.currentRoute.value.path !== target) {
      router.push(target)
      return
    }
  }

  onMounted(() => {
    poll()
    timer = setInterval(poll, INTERVAL)
  })
  onUnmounted(() => clearInterval(timer))

  return { state, error, poll }
}