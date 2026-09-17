import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { compileScript, parse } from '@vue/compiler-sfc'
import { transformSync } from 'esbuild'
import { ref, computed, reactive, watch, nextTick } from 'vue'
import { localBoardForCreation } from '../src/gameConfig.js'
import * as random from '../src/random.js'
import { nextRoomId } from '../src/random.js'
import { calculateResult } from '../src/result.js'

// Execute the actual component setup with mocked HTTP/lifecycle boundaries.
function load(file, overrides = {}) {
  const mounted = [], unmounted = [], watchers = []
  if (file === 'views/WaitingRoomView.vue' && !overrides.keepStorage) {
    const saved = new Map()
    globalThis.localStorage = { getItem: key => saved.get(key) ?? null, setItem: (key, value) => saved.set(key, value) }
  }
  const state = ref(null)
  const applied = []
  const modules = {
    vue: { ref, computed, reactive, watch: (source, callback, options) => { watchers.push(callback); return watch(source, callback, options) }, onMounted: f => mounted.push(f), onUnmounted: f => unmounted.push(f) },
    'vue-router': { useRouter: () => ({ push() {}, currentRoute: ref({ path: '/ops' }) }) },
    '../random': random,
    './AvatarField.vue': {},
    '../result': { calculateResult },
    '../api': { post: async () => ({ ok: true }) },
    '../store': { creds: () => ({ roomid: 'R', userid: 'A' }) },
    '../useRoomState': { useRoomState: () => ({ state, error: ref(null), poll: async () => ({ ok: true, phase: 'reveal' }), applyState: s => { state.value = s; applied.push(s) } }) },
    '../gameConfig': { roleName: x => x, roleIcon: () => '', errorText: x => x, localBoardForCreation, sortPlayers: (_, x) => x, ROLE_ORDER: ['werewolf','seer','robber','troublemaker','villager'], boardTemplate: () => ({ villager: 6 }) },
    '../components/ConfirmDialog.vue': {},
    '../avatar': { avatarUrl() {}, getMyAvatar() {} },
    '../playerOrder': { sortPlayers: (_, x) => x },
    ...overrides,
  }
  let source = readFileSync(new URL(`../src/${file}`, import.meta.url), 'utf8')
  if (file.endsWith('.vue')) source = compileScript(parse(source).descriptor, { id: 'test' }).content
  const cjs = transformSync(source, { format: 'cjs' }).code
  const module = { exports: {} }
  new Function('require', 'module', 'exports', cjs)(name => {
    assert.ok(modules[name], `unexpected import ${name}`)
    return modules[name]
  }, module, module.exports)
  const instance = file.endsWith('.vue') ? module.exports.default.setup({}, { expose() {} }) : module.exports
  return { instance, state, mounted, unmounted, applied, watchers }
}

test('ops countdown uses the server end time and waits for phase transition at zero', () => {
  const { instance: c, state } = load('views/OperationView.vue')
  c.now.value = 100000
  state.value = { phase: 'op', op_end_time_ms: 147030 }
  assert.equal(c.countdown.value, '47.03')
  c.now.value = 146020
  assert.equal(c.countdown.value, '1.01')
  c.now.value = 147029
  assert.equal(c.countdown.value, '0.01')
  c.now.value = 147030
  assert.equal(c.countdown.value, '跳转中...')
  c.now.value = 150000
  assert.equal(c.countdown.value, '跳转中...')
})

test('minion replay explicitly reports no werewolves', () => {
  const { instance: c } = load('views/ResultView.vue')
  assert.equal(c.opSentence({ type: 'minion', minion: 'A', wolves: [] }), '💀 爪牙 A 得知场上没有狼人。')
  assert.equal(c.opSentence({ type: 'minion', minion: 'A', wolves: ['B', 'C'] }), '💀 爪牙 A 得知了狼人是：B、C')
})

test('night action can retry after failure; seer needs exactly two centers', async () => {
  let calls = 0
  const { instance: c, state } = load('views/OperationView.vue', {
    '../api': { post: async () => ++calls === 1 ? { ok: false, error: 'network_error' } : { ok: true, phase: 'op' } },
  })
  state.value = { role: 'seer' }
  c.mode.value = 'center'; c.sel.picks = [0]
  assert.equal(c.completed(), false)
  c.sel.picks = [0, 2]
  assert.equal(c.completed(), true)
  await c.submit(); assert.equal(c.err.value, 'network_error')
  await c.submit(); assert.equal(c.err.value, ''); assert.equal(calls, 2)
})

test('vote retries after failure and excludes self', async () => {
  let calls = 0
  const { instance: c } = load('views/RevealView.vue', {
    '../api': { post: async () => ++calls === 1 ? { ok: false, error: 'network_error' } : { ok: true, phase: 'reveal', voted: true } },
  })
  c.me.value = { users: [{ userid: 'A' }, { userid: 'B' }] }
  assert.deepEqual(c.users.value.map(u => u.userid), ['B'])
  await c.vote(); await c.vote()
  assert.equal(calls, 2); assert.equal(c.err.value, '')
})

test('reveal and result loaders recover after a failed fetch', async () => {
  for (const [file, method] of [['RevealView', 'loadReveal'], ['ResultView', 'loadResult']]) {
    let calls = 0
    const { instance: c } = load(`views/${file}.vue`, { '../api': { post: async () => ++calls === 1 ? { ok: false, error: 'network_error' } : { ok: true } } })
    await c[method](); assert.equal(c.err.value, 'network_error')
    await c[method](); assert.equal(c.err.value, ''); assert.equal(c.loading.value, false)
  }
})

test('polls are deduplicated and old responses cannot override mutation or unmount', async () => {
  let resolve, calls = 0
  const { instance, unmounted } = load('useRoomState.js', {
    './api': { post: () => { calls++; return new Promise(r => { resolve = r }) } },
    './store': { creds: () => ({ roomid: 'R' }) },
  })
  const c = instance.useRoomState()
  const pending = c.poll()
  assert.equal(c.poll(), pending); assert.equal(calls, 1)
  c.applyState({ ok: true, phase: 'reveal' })
  resolve({ ok: true, phase: 'op' }); await pending
  assert.equal(c.state.value.phase, 'reveal')
  const late = c.poll()
  unmounted.forEach(f => f())
  resolve({ ok: true, phase: 'result' }); await late
  assert.equal(c.state.value.phase, 'reveal')
})

test('board edits stay private through polling and only explicit submit saves them', async () => {
  const calls = []
  const { instance: c, state } = load('views/WaitingRoomView.vue', {
    '../api': { post: async (path, body) => {
      calls.push([path, body.board]); return { ok: true, board: body.board, phase: 'op' }
    } },
  })
  state.value = { ok: true, phase: 'waiting', is_owner: true, userCount: 3, board: { villager: 6 } }
  await nextTick()
  c.adjust('villager', -1); c.adjust('werewolf', 1)
  assert.equal(calls.length, 0)
  assert.deepEqual(c.currentBoard(), { villager: 6 })
  await nextTick()
  assert.deepEqual(c.board.value, { villager: 5, werewolf: 1 })
  await c.start(); assert.equal(calls.length, 0)
  await c.saveBoard()
  assert.deepEqual(c.currentBoard(), { villager: 5, werewolf: 1 })
  await c.start()
  assert.deepEqual(calls.map(([path]) => path), ['set_board', 'start_game'])
})

test('failed template submission keeps draft and blocks start', async () => {
  let calls = 0
  const { instance: c, state } = load('views/WaitingRoomView.vue', {
    '../api': { post: async () => { calls++; return { ok: false, error: 'network_error' } } },
  })
  state.value = { phase: 'waiting', is_owner: true, userCount: 3, board: { villager: 6 } }
  await nextTick()
  c.adjust('villager', -1); c.adjust('werewolf', 1)
  await c.saveBoard(); await c.start()
  assert.equal(calls, 1)
  assert.equal(c.dirty.value, true)
  assert.equal(c.saving.value, false)
  assert.deepEqual(c.currentBoard(), { villager: 6 })
})

test('house rules: unique highest, ties, minion fallback and all abstain', () => {
  const cases = [
    [['werewolf','villager','villager'], ['B','C','A'], true, null],
    [['werewolf','villager','villager'], ['', 'A', ''], true, 'A'],
    [['werewolf','minion','villager'], ['B','','B'], false, 'B'],
    [['minion','villager','villager'], ['B','A',''], true, null],
    [['minion','villager','villager'], ['B','C',''], false, null],
    [['villager','villager','villager'], ['','',''], true, null],
    [['villager','villager','villager'], ['B','',''], false, 'B'],
    [['villager','villager','villager'], ['B','C','A'], false, null],
    [['werewolf','villager','villager'], ['','',''], false, null],
    [['minion','villager','villager'], ['','',''], false, null],
  ]
  for (const [roles, targets, good, executed] of cases) {
    const players = roles.map((role, i) => ({ userid: 'ABC'[i], role,
      choice: { type: 'wolf', target: 'center_0' }, vote_target: targets[i] }))
    const result = calculateResult({ players, center: ['villager','seer','robber'] })
    assert.equal(result.good_win, good, JSON.stringify([roles, targets]))
    assert.equal(result.executed, executed)
    for (const p of result.players) assert.equal(p.won, good !== ['werewolf','minion'].includes(p.final_role))
  }
})

test('raw actions derive ordered replay, final cards and winner without applying decoys', () => {
  const players = [
    { userid: 'A', role: 'robber', choice: { type: 'robber', target: 'C' }, vote_target: 'C' },
    { userid: 'B', role: 'troublemaker', choice: { type: 'troublemaker', target: 'A', target2: 'C' }, vote_target: 'C' },
    { userid: 'C', role: 'werewolf', choice: { type: 'wolf', target: 'center_0' }, vote_target: '' },
    { userid: 'D', role: 'villager', choice: { type: 'robber', target: 'C' }, vote_target: '' },
  ]
  const result = calculateResult({ players, center: ['seer','villager','minion'] })
  assert.deepEqual(result.players.map(p => p.final_role), ['robber','troublemaker','werewolf','villager'])
  assert.equal(result.ops.find(op => op.type === 'robber').robber_new, 'werewolf')
  assert.equal(result.ops.filter(op => op.type === 'robber').length, 1)
  assert.equal(result.good_win, true)
  // Derivation does not mutate the source facts.
  assert.equal(players[0].role, 'robber')
  assert.equal(players[0].final_role, undefined)
})

test('wolf and seer see the same ordered center card in replay', () => {
  const result = calculateResult({ center: ['robber','minion','troublemaker'], players: [
    { userid: 'A', role: 'werewolf', choice: { type: 'wolf', target: 'center_1' }, vote_target: '' },
    { userid: 'B', role: 'seer', choice: { type: 'seer', center_picks: [1,2] }, vote_target: '' },
    { userid: 'C', role: 'villager', choice: { type: 'wolf', target: 'center_0' }, vote_target: '' },
  ] })
  const wolf = result.ops.find(op => op.type === 'lone_wolf')
  const seer = result.ops.find(op => op.type === 'seer')
  assert.equal(wolf.card, 'minion')
  assert.equal(wolf.card, seer.peeked[0])
  assert.deepEqual(seer.peeked, ['minion','troublemaker'])
})


test('local template survives room updates, joins, submission responses and remounts', async () => {
  const { instance: c, state } = load('views/WaitingRoomView.vue', {
    '../api': { post: async () => ({ ok: true, board: { villager: 99 } }) },
  })
  const local = { ...c.board.value }
  state.value = { phase: 'waiting', is_owner: true, userCount: 3, board: { werewolf: 6 } }
  await nextTick()
  assert.deepEqual(c.board.value, local)
  c.adjust('villager', -1)
  c.adjust('werewolf', 1)
  const draft = { ...c.board.value }
  state.value = { ...state.value, userCount: 4, board: { villager: 7 } }
  await nextTick()
  assert.deepEqual(c.board.value, draft)
  assert.deepEqual(JSON.parse(localStorage.getItem('waitingBoard')), draft)
  await c.saveBoard()
  await nextTick()
  assert.deepEqual(c.board.value, draft)
  assert.deepEqual(c.currentBoard(), { villager: 99 })
  // Visiting as a guest must not replace the browser's draft either.
  state.value = { ...state.value, is_owner: false, board: { seer: 7 } }
  await nextTick()
  assert.deepEqual(JSON.parse(localStorage.getItem('waitingBoard')), draft)
  const { instance: restored } = load('views/WaitingRoomView.vue', { keepStorage: true })
  for (const role of restored.ROLE_ORDER) {
    assert.equal(restored.board.value[role] || 0, draft[role] || 0)
  }
})

test('pack wolf decoy swaps never affect final roles or replay', () => {
  const result = calculateResult({ players: [
    { userid: 'A', role: 'werewolf', choice: { type: 'robber', target: 'C' }, vote_target: '' },
    { userid: 'B', role: 'werewolf', choice: { type: 'troublemaker', target: 'A', target2: 'C' }, vote_target: '' },
    { userid: 'C', role: 'villager', choice: { type: 'seer', center_picks: [0,1] }, vote_target: '' },
  ] })
  assert.deepEqual(result.players.map(p => p.final_role), ['werewolf','werewolf','villager'])
  assert.deepEqual(result.ops.map(op => op.type), ['wolf'])
})


test('base 62 room successor carries, preserves width and wraps deterministically', () => {
  for (const [before, after] of [['a','b'], ['z','A'], ['Z','0'], ['8','9'],
    ['9','ba'], ['a9','ba'], ['009','01a'], ['99999','baaaaa'],
    ['999999','aaaaaa'], ['abcDEF','abcDEG'], ['', 'a'], ['bad!', 'a']]) {
    assert.equal(nextRoomId(before), after)
  }
})

function nextRoomHarness(post) {
  const routes = [], auth = []
  const component = load('views/ResultView.vue', {
    '../api': { post },
    '../store': { creds: () => ({ roomid: 'z', userid: 'A', userpsw: '1234' }), setAuth: value => auth.push(value) },
    'vue-router': { useRouter: () => ({ push: path => routes.push(path) }) },
  })
  return { ...component, routes, auth }
}

test('creating an existing next room joins it with the same credentials', async () => {
  const calls = []
  const { instance: c, routes, auth } = nextRoomHarness(async (path, body) => {
    calls.push([path, body])
    return path === 'create_room' ? { ok: false, error: 'roomid_taken' } : { ok: true, phase: 'waiting', avatar: 'moon' }
  })
  await c.enterNext(true)
  assert.deepEqual(calls.map(x => x[0]), ['create_room', 'join_room'])
  assert.equal(calls[1][1].roomid, 'A')
  assert.equal(calls[1][1].userpsw, '1234')
  assert.deepEqual(routes, ['/waitingroom'])
  assert.equal(auth[0].avatar, 'moon')
})

test('auto join retries missing rooms and cancellation ignores in-flight success', async (t) => {
  t.mock.timers.enable({ apis: ['setTimeout'] })
  let calls = 0, resolve
  const { instance: c, routes, auth } = nextRoomHarness(async () => {
    calls++
    if (calls === 1) return { ok: false, error: 'room_not_found' }
    return new Promise(r => { resolve = r })
  })
  await c.enterNext()
  assert.equal(c.autoJoin.value, true)
  assert.match(c.nextMessage.value, /等待房主/)
  t.mock.timers.tick(2000)
  assert.equal(calls, 2)
  c.cancelAutoJoin()
  resolve({ ok: true, phase: 'waiting' })
  await Promise.resolve(); await Promise.resolve()
  assert.equal(c.autoJoin.value, false)
  assert.deepEqual(routes, [])
  assert.deepEqual(auth, [])
  t.mock.timers.tick(10000)
  assert.equal(calls, 2)
})

test('auto join succeeds after creation and stops on permanent errors or unmount', async (t) => {
  t.mock.timers.enable({ apis: ['setTimeout'] })
  for (const outcome of [{ ok: true, phase: 'waiting' }, { ok: false, error: 'room_full' }, { ok: false, error: 'wrong_password' }, { ok: false, error: 'room_started' }]) {
    let calls = 0
    const { instance: c, routes, unmounted } = nextRoomHarness(async () => ++calls === 1 ? { ok: false, error: 'room_not_found' } : outcome)
    await c.enterNext()
    t.mock.timers.tick(2000)
    await Promise.resolve(); await Promise.resolve()
    assert.equal(c.autoJoin.value, false)
    assert.deepEqual(routes, outcome.ok ? ['/waitingroom'] : [])
    if (!outcome.ok) assert.equal(c.nextMessage.value, outcome.error)
    unmounted.forEach(f => f())
    t.mock.timers.tick(10000)
    assert.equal(calls, 2)
  }
  let calls = 0
  const { instance: c, unmounted } = nextRoomHarness(async () => { calls++; return { ok: false, error: 'room_not_found' } })
  await c.enterNext()
  unmounted.forEach(f => f())
  t.mock.timers.tick(10000)
  assert.equal(calls, 1)
})


test('both create entry points send the saved template in the creation request', async () => {
  const board = { werewolf: 1, seer: 1, villager: 4 }
  localStorage.setItem('waitingBoard', JSON.stringify(board))
  localStorage.setItem('roomId', 'New')
  localStorage.setItem('userId', 'A')
  localStorage.setItem('userPsw', '1234')
  for (const file of ['CreateRoomView', 'ResultView']) {
    const calls = []
    const { instance: c } = load(`views/${file}.vue`, {
      '../api': { post: async (path, body) => { calls.push([path, body]); return { ok: true } } },
      '../store': { creds: () => ({ roomid: 'Old', userid: 'A', userpsw: '1234' }), setAuth() {} },
    })
    if (file === 'CreateRoomView') await c.submit()
    else await c.enterNext(true)
    assert.equal(calls.length, 1)
    assert.equal(calls[0][0], 'create_room')
    assert.deepEqual(calls[0][1].board, board)
  }
})

test('unreadable local templates safely fall back to the server default', () => {
  localStorage.setItem('waitingBoard', '{broken')
  assert.equal(localBoardForCreation(), null)
  const previous = globalThis.localStorage
  try {
    globalThis.localStorage = { getItem() { throw new Error('unavailable') } }
    assert.equal(localBoardForCreation(), null)
  } finally { globalThis.localStorage = previous }
})
