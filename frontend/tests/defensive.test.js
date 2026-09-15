import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { compileScript, parse } from '@vue/compiler-sfc'
import { transformSync } from 'esbuild'
import { ref, computed, reactive } from 'vue'
import { calculateResult } from '../src/result.js'

// Execute the actual component setup with mocked HTTP/lifecycle boundaries.
function load(file, overrides = {}) {
  const mounted = [], unmounted = [], watchers = []
  const state = ref(null)
  const applied = []
  const modules = {
    vue: { ref, computed, reactive, watch: (_, callback) => watchers.push(callback), onMounted: f => mounted.push(f), onUnmounted: f => unmounted.push(f) },
    'vue-router': { useRouter: () => ({ push() {}, currentRoute: ref({ path: '/ops' }) }) },
    '../result': { calculateResult },
    '../api': { post: async () => ({ ok: true }) },
    '../store': { creds: () => ({ roomid: 'R', userid: 'A' }) },
    '../useRoomState': { useRoomState: () => ({ state, error: ref(null), poll: async () => ({ ok: true, phase: 'reveal' }), applyState: s => { state.value = s; applied.push(s) } }) },
    '../gameConfig': { roleName: x => x, roleIcon: () => '', errorText: x => x, sortPlayers: (_, x) => x, ROLE_ORDER: ['werewolf','seer','robber','troublemaker','villager'], boardTemplate: () => ({ villager: 6 }) },
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
  assert.equal(c.countdown.value, '47:03')
  c.now.value = 146020
  assert.equal(c.countdown.value, '1:01')
  c.now.value = 147029
  assert.equal(c.countdown.value, '0:01')
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
  const { instance: c, state, watchers } = load('views/WaitingRoomView.vue', {
    '../api': { post: async (path, body) => {
      calls.push([path, body.board]); return { ok: true, board: body.board, phase: 'op' }
    } },
  })
  state.value = { ok: true, phase: 'waiting', is_owner: true, userCount: 3, board: { villager: 6 } }
  watchers[0](state.value)
  c.adjust('villager', -1); c.adjust('werewolf', 1)
  assert.equal(calls.length, 0)
  assert.deepEqual(c.currentBoard(), { villager: 6 })
  watchers[0](state.value)
  assert.deepEqual(c.board.value, { villager: 5, werewolf: 1 })
  await c.start(); assert.equal(calls.length, 0)
  await c.saveBoard()
  assert.deepEqual(c.currentBoard(), { villager: 5, werewolf: 1 })
  await c.start()
  assert.deepEqual(calls.map(([path]) => path), ['set_board', 'start_game'])
})

test('failed template submission keeps draft and blocks start', async () => {
  let calls = 0
  const { instance: c, state, watchers } = load('views/WaitingRoomView.vue', {
    '../api': { post: async () => { calls++; return { ok: false, error: 'network_error' } } },
  })
  state.value = { phase: 'waiting', is_owner: true, userCount: 3, board: { villager: 6 } }
  watchers[0](state.value)
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


test('cached templates never override the submitted room template', () => {
  globalThis.localStorage = { getItem: () => '{"werewolf":6}', setItem() {} }
  const { instance: c, watchers } = load('views/WaitingRoomView.vue')
  watchers[0]({ phase: 'waiting', userCount: 3, board: { villager: 6 } })
  assert.deepEqual(c.board.value, { villager: 6 })
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
