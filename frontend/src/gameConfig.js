// Display-side configuration: every human sentence / role name / error text
// lives here, mapped from stable backend codes (see design.md ``%8``).

export const ROLE_DISPLAY = {
  werewolf: { name: '狼人', emoji: '🐺', faction: 'evil' },
  minion: { name: '爪牙', emoji: '💀', faction: 'evil' },
  seer: { name: '预言家', emoji: '🔮', faction: 'good' },
  robber: { name: '强盗', emoji: '🥷', faction: 'good' },
  troublemaker: { name: '捣蛋鬼', emoji: '🃏', faction: 'good' },
  insomniac: { name: '失眠者', emoji: '🌙', faction: 'good' },
  villager: { name: '村民', emoji: '👤', faction: 'good' },
}

export const roleName = (code) => ROLE_DISPLAY[code]?.name || code
export const roleIcon = (code) => ROLE_DISPLAY[code]?.emoji || '❔'

// Real operable interfaces; only lone wolves peek. Other roles use local cover clicks.
export const OPERATION_ROLES = ['seer', 'robber', 'troublemaker', 'werewolf']

// Every room starts with two wolves, two villagers, and one of every other role.
export function boardTemplate() {
  return Object.fromEntries(Object.keys(ROLE_DISPLAY).map(role =>
    [role, ['werewolf', 'villager'].includes(role) ? 2 : 1]))
}

export const ROLE_ORDER = ['werewolf', 'seer', 'robber', 'troublemaker', 'insomniac', 'minion', 'villager']

// Short English backend codes -> Chinese sentences.
export const ERROR_MESSAGES = {
  roomid_taken: '房间号已被占用',
  bad_request: '请求格式错误',
  method_not_allowed: '请求方法不支持',
  room_not_found: '房间不存在',
  wrong_password: '密码错误',
  bad_credentials: '凭据不正确（房间号 / 玩家名 / 密码）',
  room_full: '房间已满（最多 10 人）',
  room_started: '房间已开局，无法加入',
  not_host: '只有房主可以执行此操作',
  not_waiting: '房间已不在等待阶段',
  bad_players_count: '人数不合法（需 3~10 人）',
  bad_board: '牌组不合法（总牌数须等于 人数+3）',
  not_in_op: '当前不在操作阶段',
  bad_choice: '操作不合法',
  already_voted: '你已经投过票了',
  bad_target: '目标不合法',
  not_in_reveal: '当前不在投票阶段',
  not_done: '投票尚未全部完成',
  network_error: '网络错误，请检查连接',
  http_403: '请求被拒绝（CSRF），请刷新页面',
  http_404: '接口不存在',
  http_500: '服务器出错',
}

export function errorText(code) {
  return ERROR_MESSAGES[code] || (code ? `错误：${code}` : '未知错误')
}

const VERDICT = {
  no_evil_players: '玩家中没有狼人或爪牙，全员弃权，好人阵营获胜 🎉',
  no_evil_but_votes: '玩家中没有狼人或爪牙，但有人投票，全体玩家落败',
  minion_in_tie: '场上无狼人，平票者中有爪牙，好人阵营获胜 🎉',
  wolf_executed: '狼人被处决，好人阵营获胜 🎉',
  minion_executed_no_wolf: '爪牙被处决，好人阵营获胜 🎉',
  villager_executed: '未投出关键目标，狼人阵营获胜',
  no_execution: '无人被处决，狼人阵营获胜',
  wolf_in_tie: '平票，但平票者中存在狼人，狼人阵营落败，好人阵营获胜 🎉',
}

export const verdictText = (code) => VERDICT[code] || code

export const PHASE_TEXT = {
  waiting: '等待开始',
  op: '行动阶段',
  reveal: '揭晓与投票',
  result: '结算',
}

// Send the saved draft as-is; the server validates it and falls back safely.
export function localBoardForCreation() {
  try {
    return JSON.parse(localStorage.getItem('waitingBoard'))
  } catch {
    return null
  }
}
