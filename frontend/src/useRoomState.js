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
  let active = true
  let pending = null
  let revision = 0

  function applyState(res) {
    if (!active || !res || !res.ok) return
    revision++
    error.value = null
    state.value = res
    if (onState) onState(res)
    const target = PHASE_ROUTE[res.phase]
    if (target && router.currentRoute.value.path !== target) router.push(target)
  }

  function poll() {
    if (!active || !creds().roomid) return Promise.resolve(null)
    if (pending) return pending
    const version = revision
    pending = (async () => {
      const res = await post('room_state', creds())
      if (!active || version !== revision) return null
      if (!res?.ok) {
        error.value = res?.error || 'network_error'
        return null
      }
      applyState(res)
      return res
    })().finally(() => { pending = null })
    return pending
  }

  onMounted(() => {
    poll()
    timer = setInterval(poll, INTERVAL)
  })
  onUnmounted(() => { active = false; clearInterval(timer) })

  return { state, error, poll, applyState }
}