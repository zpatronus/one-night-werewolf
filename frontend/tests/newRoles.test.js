import test from 'node:test'
import assert from 'node:assert/strict'
import { calculateResult } from '../src/result.js'

const player = (userid, role, vote_target = '', choice = {}, shot_target = null) => ({ userid, role, vote_target, choice, shot_target })

test('drunk swaps after troublemaker and before insomniac', () => {
  const result = calculateResult({ center: ['hunter', 'villager', 'villager'], players: [
    player('A', 'drunk', '', { type: 'drunk', target: 'center_0' }),
    player('B', 'troublemaker', '', { type: 'troublemaker', target: 'A', target2: 'C' }),
    player('C', 'insomniac'),
  ] })
  assert.deepEqual(result.players.map(p => p.final_role), ['hunter', 'troublemaker', 'drunk'])
  assert.equal(result.finalCenter[0], 'insomniac')
  assert.deepEqual(result.ops.map(o => o.type), ['troublemaker', 'drunk', 'insomniac'])
})

test('hunter shooting a wolf changes the winner', () => {
  const result = calculateResult({ players: [player('A', 'hunter', 'C', {}, 'C'), player('B', 'villager', 'A'), player('C', 'werewolf', 'A', { target: 'center_0' })], center: ['villager'] })
  assert.deepEqual(result.executions, ['A', 'C'])
  assert.equal(result.good_win, true)
})

test('shot-only hunters cannot chain shots', () => {
  const result = calculateResult({ players: [player('A', 'hunter', 'C', {}, 'B'), player('B', 'hunter', 'A', {}, 'C'), player('C', 'werewolf', 'A', { target: 'center_0' })], center: ['villager'] })
  assert.deepEqual(result.executions, ['A', 'B'])
  assert.equal(result.good_win, false)
})

test('every tied hunter contributes a shot', () => {
  const result = calculateResult({ players: [player('A', 'hunter', 'B', {}, 'B'), player('B', 'hunter', 'A', {}, 'C'), player('C', 'werewolf', '', { target: 'center_0' })], center: ['villager'] })
  assert.deepEqual(result.executions, ['B', 'A', 'C'])
  assert.equal(result.shots.length, 2)
  assert.equal(result.good_win, true)
})
