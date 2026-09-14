// Result data is public only after all votes are final. Derive every display
// from the original cards, raw choices and raw votes; nothing is persisted here.
export function calculateResult({ players = [], center = [] } = {}) {
  const cards = new Map(players.map(p => [p.userid, p.role]))
  const ops = []
  const wolves = players.filter(p => p.role === 'werewolf').map(p => p.userid)
  if (wolves.length) ops.push({ type: 'wolf', wolves })
  for (const p of players) {
    if (p.role === 'minion') ops.push({ type: 'minion', minion: p.userid, wolves })
  }
  if (wolves.length === 1) {
    const wolf = players.find(p => p.userid === wolves[0])
    const index = Number(wolf.choice.target.split('_')[1])
    ops.push({ type: 'lone_wolf', lone_wolf: wolf.userid, center: index, card: center[index] })
  }
  for (const p of players) {
    if (p.role !== 'seer') continue
    const c = p.choice
    ops.push({ type: 'seer', seer: p.userid, ...c,
      peeked: c.center_picks ? c.center_picks.map(i => center[i]) : [cards.get(c.target)] })
  }
  for (const p of players) {
    if (p.role !== 'robber') continue
    const target = p.choice.target
    const before = cards.get(p.userid)
    cards.set(p.userid, cards.get(target)); cards.set(target, before)
    ops.push({ type: 'robber', robber: p.userid, target,
      robber_new: cards.get(p.userid), target_new: cards.get(target) })
  }
  for (const p of players) {
    if (p.role !== 'troublemaker') continue
    const { target: a, target2: b } = p.choice
    const before = cards.get(a)
    cards.set(a, cards.get(b)); cards.set(b, before)
    ops.push({ type: 'troublemaker', troublemaker: p.userid, a, b,
      a_new: cards.get(a), b_new: cards.get(b) })
  }
  for (const p of players) {
    if (p.role === 'insomniac') ops.push({ type: 'insomniac', insomniac: p.userid, card: cards.get(p.userid) })
  }

  const votes = Object.create(null)
  for (const p of players) {
    if (p.vote_target) votes[p.vote_target] = (votes[p.vote_target] || 0) + 1
  }
  const highest = Math.max(0, ...Object.values(votes))
  const top = Object.keys(votes).filter(uid => votes[uid] === highest)
  const executed = top.length === 1 ? top[0] : null
  const roles = [...cards.values()]
  const noEvil = !roles.some(role => role === 'werewolf' || role === 'minion')
  const enemy = roles.includes('werewolf') ? 'werewolf' : 'minion'
  const caught = top.some(uid => cards.get(uid) === enemy)
  const good_win = noEvil ? players.every(p => p.vote_target === '') : caught
  let reason
  if (noEvil) reason = good_win ? 'no_evil_players' : 'no_evil_but_votes'
  else if (caught && top.length > 1) reason = enemy === 'werewolf' ? 'wolf_in_tie' : 'minion_in_tie'
  else if (caught) reason = enemy === 'werewolf' ? 'wolf_executed' : 'minion_executed_no_wolf'
  else reason = executed ? 'villager_executed' : 'no_execution'

  return { votes, executed, good_win, reason, ops, players: players.map(p => {
    const final_role = cards.get(p.userid)
    const evil = final_role === 'werewolf' || final_role === 'minion'
    return { ...p, final_role, won: good_win ? !evil : evil }
  }) }
}
