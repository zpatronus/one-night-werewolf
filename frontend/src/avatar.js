// Avatar identity is a filename (the same 50-avatar set the Avalon project
// ships). The current user's filename is stored in localStorage under "avatar".
// SVG contents are cached separately (key "avatarFile:<name>") so an avatar
// asset is only fetched when that file isn't already cached, mirroring Avalon's
// avatar.js exactly.
import { base } from './store'

const CURRENT_AVATAR_KEY = 'avatar'
const FILE_CACHE_PREFIX = 'avatarFile:'
const pending = new Set()

// Stable, sorted list of avatar file names (without the .svg extension — the
// backend stores names the same way).
const FILES = [
  'agent-halloween-japanese-man-ninja',
  'alien-devil-halloween-mascot-monster',
  'angel-god-gurdian-halloween-wing',
  'avatar-costume-elf-fairy-halloween',
  'beast-halloween-monster-werewolf-costume',
  'boy-character-costume-halloween-pirate',
  'bride-dead-ghost-halloween-horror',
  'bull-greek-minos-minotaur-monster',
  'burial-robes-ghost-halloween-japanese',
  'character-costume-ghost-halloween-horror',
  'character-creature-mascot-snow-winter',
  'character-evil-halloween-horror-monster',
  'character-fantasy-gorgon-medusa-monster',
  'character-grim-halloween-reaper-scythe',
  'chinese-fangs-halloween-horror-vampire',
  'circus-clown-fear-halloween-horror',
  'costume-dead-halloween-head-horror',
  'costume-frankenstein-halloween-monster-scary',
  'costume-ghost-goblin-halloween-horror',
  'costume-glasses-goggles-halloween-hat',
  'creature-fantasy-monster-ogre-orc',
  'crystal-ball-magic-magician-witch',
  'cybernetic-cyborg-halloween-machine-robot',
  'cyborg-halloween-machine-robot-teen',
  'cyclops-halloween-holidays-horror-stories',
  'dead-death-fear-grim-horror',
  'dead-halloween-horror-scary-zombie',
  'demon-devil-halloween-lucifer-satan',
  'dracula-halloween-horror-vampire-costume',
  'fairy-fantasy-horn-legend-satyr',
  'farm-halloween-horror-scarecrow-costume',
  'fear-ghost-halloween-horror-scary',
  'fear-halloween-horror-mummy-scary',
  'fear-jack-lantern-scary-spooky',
  'friday-halloween-mask-thirteen-costume',
  'ghost-halloween-horror-nightmare-nun',
  'ghost-halloween-horror-pirate-skeleton',
  'ghost-queen-devil-evil-halloween',
  'halloween-gnome-vampire-dwarf-costume-2',
  'halloween-gnome-vampire-dwarf-costume',
  'halloween-hat-witch-horror-scary',
  'halloween-tentacles-octopus-elephant-cthulhu',
  'medieval-executioner-ancient-age-middle',
  'medieval-steel-warrior-armor-knight',
  'one-eye-rectangle-monster-cartoon',
  'samurai-warrior-armor-japan-culture',
  'scientist-professor-glasses-halloween-costume',
  'viking-halloween-costume-character-avatar',
  'wizard-treat-warlock-cane-trick',
  'zombie-scary-horror-halloween-costume',
]
export const AVATARS = [...FILES].sort()

function isValidAvatar(file) {
  return Boolean(file && AVATARS.includes(file))
}

export function randomAvatar() {
  return AVATARS[Math.floor(Math.random() * AVATARS.length)] || ''
}

export function getMyAvatar() {
  const stored = localStorage.getItem(CURRENT_AVATAR_KEY)
  if (isValidAvatar(stored)) return stored

  const picked = randomAvatar()
  if (picked) localStorage.setItem(CURRENT_AVATAR_KEY, picked)
  return picked
}

export function setMyAvatar(file) {
  if (isValidAvatar(file)) localStorage.setItem(CURRENT_AVATAR_KEY, file)
  return file
}

function cacheKey(file) {
  return FILE_CACHE_PREFIX + file
}

function cacheFile(file, assetUrl) {
  if (pending.has(file)) return
  pending.add(file)
  fetch(assetUrl)
    .then((response) => {
      if (!response.ok) throw new Error('avatar request failed')
      return response.text()
    })
    .then((svg) => localStorage.setItem(cacheKey(file), svg))
    .catch(() => {})
    .finally(() => pending.delete(file))
}

// Check the content cache first; on a miss, use the static asset for this
// render and populate localStorage for subsequent renders.
export function avatarUrl(file) {
  const safeFile = isValidAvatar(file) ? file : AVATARS[0]
  if (!safeFile) return ''

  const cached = localStorage.getItem(cacheKey(safeFile))
  if (cached) return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(cached)}`

  const assetUrl = `${base}avatars/${safeFile}.svg`
  cacheFile(safeFile, assetUrl)
  return assetUrl
}