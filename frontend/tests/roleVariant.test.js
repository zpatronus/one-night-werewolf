import test from 'node:test'
import assert from 'node:assert/strict'
import { existsSync } from 'node:fs'
import { roleVariant, localDateKey } from '../src/roleVariant.js'

const roles = ['werewolf', 'minion', 'seer', 'robber', 'troublemaker', 'insomniac', 'villager']

test('room/user role choices survive dates and repeated joins with mixed variants', () => {
  const choices = roles.map(role => roleVariant(role, { roomid: 'ROOM', userid: 'Alice', date: '2026-09-18' }))
  assert.deepEqual(roles.map(role => roleVariant(role, { roomid: 'ROOM', userid: 'Alice', date: '2030-01-01' })), choices)
  assert.ok(new Set(choices).size > 1)
  for (const role of roles) {
    const variants = new Set(Array.from({ length: 100 }, (_, i) => roleVariant(role, { roomid: 'ROOM', userid: `User${i}` })))
    assert.deepEqual(variants, new Set([1, 2, 3]))
  }
  assert.notDeepEqual(roles.map(role => roleVariant(role, { roomid: 'ROOM', userid: 'Bob' })), choices)
  assert.notDeepEqual(roles.map(role => roleVariant(role, { roomid: 'OTHER', userid: 'Alice' })), choices)
})

test('homepage choices depend on local calendar date and role, with three assets for every role', () => {
  assert.equal(localDateKey(new Date(2026, 8, 18, 23, 59)), '2026-09-18')
  const today = roles.map(role => roleVariant(role, { date: '2026-09-18' }))
  assert.deepEqual(roles.map(role => roleVariant(role, { date: '2026-09-18' })), today)
  assert.notDeepEqual(roles.map(role => roleVariant(role, { date: '2026-09-19' })), today)
  for (const role of roles) {
    for (const version of [1, 2, 3]) assert.ok(existsSync(new URL(`../src/assets/roles/${role}-${version}.webp`, import.meta.url)))
  }
})
