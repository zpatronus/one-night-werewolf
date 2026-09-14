# 一夜狼人 — View 逻辑流设计（逐页面）

> 当前数据结构、请求字段与并发约束以 [endpoint-design.md](endpoint-design.md) 为准；使用本项目自定义胜负规则。


> 配套文档：`design.md` 讲总体与后端；本文聚焦**每个 View 的组成元素、轮询节奏、跳转逻辑**。
> 技术栈：Vue 3 + Vue Router + Vuex；实时性一律 HTTP 轮询（**无 websocket**）。

---

## 0. 通用约定（所有 View 共享）

- **凭据与接口**：所有读写均 `POST`，body 带 `{roomid, userid, userpsw}`；CSRF 由 `api.js` 的 `ensureToken()` 惰性拉取，`X-CSRFToken` 头随带。URL 里绝不出现凭据。
- **响应协议**：一律 `{"ok": bool, ...}`（HTTP 200），靠 `ok` 判断；错误用稳定英文 code，前端 `gameConfig.js` 翻译。
- **localStorage 身份**：`roomId` / `userId` / `userPsw` 由 Create/Join 写入；对局各 View 从这三者取当前玩家的房间与凭据。
- **唯一轮询端点 `/api/room_state/`（核心约定）**：waiting 与三个对局 View 的间歇轮询**归一到一个端点 `/api/room_state/`**，响应携带 `phase`（`waiting | op | reveal | result`）+ 该 phase 的渲染数据（见 §0.1）。不再有独立的 `/api/waiting_room/`、`/api/night_status/` 轮询。

### 0.1 唯一轮询端点 `/api/room_state/`（phase → View 路由 + phase 专属 payload）

所有间歇轮询归一到一个端点：**`POST /api/room_state/ {roomid, userid, userpsw}`**（取代原先分开的 `/api/waiting_room/` 与 `/api/night_status/`）。它永远同时给 `phase` 与**该 phase 所需的渲染数据**：

| phase | 常驻 View | `/api/room_state/` 返回的 dashboard（渲染/更新用） |
|---|---|---|
| `waiting` | `WaitingRoomView` | `users, userCount, avatars, host, is_owner, board` |
| `op` | `OperationView` | `role, my_choice, submitted, submitted_count, total_count, deadline_ms` |
| `reveal` | `RevealView` | `voted`（**仅投票进度**，不含揭晓内容——揭晓由一次性 `/api/reveal/` 给） |
| `result` | `ResultView` | 空（结果由一次性 `/api/result/` 给） |

**统一调度逻辑**（每个 View 的间歇轮询都套同一段）：
1. `mounted` 先调一次 `/api/room_state/`，以后每 `2s` 调一次；每次读 `phase`。
2. `phase` 与当前 View **不符** → `$router.push(phase → View 路由)`（刷新/断线也靠它自动归位）。
3. `phase` 与当前 View **相符** → 用该 phase 的 payload 渲染/更新本页（**不跳转**）。

> 例：`/ops` 页面轮询 `/api/room_state/`——`phase=op` 时用它渲染操作界面（`role`/`my_choice`/`deadline_ms`）；一旦 `phase` 变 `reveal` 就跳 `/reveal`。`/reveal` 同理：`phase=reveal` 渲染投票进度；变为 `result` 跳 `/result`。

---

## 1. HomeView（`/`）

**职责**：创建和加入房间说明；暂不展示游戏规则教学。

- **组成元素**：
  - masthead（标题/标语）、顶部 nav（主页 / 创建房间 / 加入房间）——来自 `App.vue`。
  - 玩法说明卡（`--help`）：如何创建房间、如何创建玩家/加入房间。
  - 更新日志卡。
  - 页脚“Visitors”。
- **轮询**：无（仅 `App.vue` 一次性拉访客计数，可忽略）。
- **跳转**：只通过顶部 nav 到 `/createroom`、`/joinroom`。

### 1.1 路由跳转图（来到 Home 时）

```
Home ──nav──▶ CreateRoom ──▶ JoinRoom ──▶ WaitingRoom ──▶ /ops ─▶ /reveal ─▶ /result
```

---

## 2. CreateRoomView（`/createroom`）

**职责**：创建房间；**创建者即房主**，所以创建动作同时绑定身份。

- **组成元素**：
  - 房间ID 输入 + “下一个”生成按钮。
  - 玩家ID 输入。
  - 玩家密码输入 + “随机”按钮。
  - 头像选择：预览框 + “随机头像” + 头像 `<dialog>`（网格选择器）。
  - Tips（密码非房间密码、明文传输、建议随机）。
  - 提交按钮 + 状态区 `info`。
- **本地记忆（mounted 载入 / input 时写入）**：`roomId`、`userId`、`userPsw`、`avatar`。
  - `userId`/`userPsw` 若为首次（无记忆）则随机生成默认值（见阿瓦隆 `getRandomUserId`/`generateRandomPsw`）。
- **校验**：
  - `roomId` ≤6 位字母/数字；`userId` ≤7 位（字母/数字/`_`）；`userPsw` ≤6 位字母/数字；非法输入的字符被回退。
  - 头像取 `getMyAvatar()`。
- **轮询**：无。
- **提交动作（仅一次 POST，成功后跳转）**：
  1. `POST /api/create_room/ {roomid, userid, userpsw, avatar}`。
  2. 成功（`ok`）→ `setMyAvatar(服务端权威avatar)` → **跳 `/waitingroom`**。
  3. 失败 → `info` 显示 `errorMessage`；网络错误 → “网络错误，请重试”。
- **跳转**：`/createroom ──✅──▶ /waitingroom`（无 2 次 POST，不重复 join）。

---

## 3. JoinRoomView（`/joinroom`）

**职责**：加入已有房间，或登录已有玩家。与阿瓦隆完全一致。

- **组成元素**：与 CreateRoom 相同（房间ID / 玩家ID / 密码 / 头像选择器 / Tips / 提交 + `info`）。
- **本地记忆 / 校验**：同上（复用同套逻辑）。
- **轮询**：无。
- **提交动作（一次 POST 定落点）**：
  `POST /api/join_room/ {roomid, userid, userpsw, avatar}`：
  - 玩家不存在 → 创建新玩家（`created=true`）；存在且密码对 → 登录（`created=false`）；密码错 → `wrong_password`。
  - 回传权威 `avatar` → `setMyAvatar(avatar)`。
  - 成功后**直接跳 `/waitingroom`**：无需再查房间状态——房间若已被开始，WaitingRoom 的 `room_state` 轮询（§0.1 统一逻辑）会立刻发现 `phase != waiting` 并把本玩家归位到对应对局 View（`/ops` 或 `/reveal`）。
- **跳转**：`/joinroom ──▶ /waitingroom`（已开局时由统一轮询自动再跳对局 View）。

---

## 4. WaitingRoomView（`/waitingroom`）

**职责**：等待玩家到齐；房主配置每种角色的板子份数并开始游戏；非房主只读等待。**板子以服务端 DB 为唯一真值来源**（见 design.md §6.6）——所有人显示的都是服务器上的同一份模板。

- **组成元素**：
  - 信息卡：房间ID / 你的玩家ID / 玩家数量。
  - “房间内的玩家”卡片网格（头像 + 名字，`playerOrder.sortPlayers` 稳定排序）。
  - 板子区块：展示**服务端当前 `board`（DB 里那份 `{role:count}` 映射）**，对所有人显示一致。
  - 房主专属：
    - **板子修改器 UI**：每种角色一个“− count +”步进控件（`0`=不下）+ 实时“已配 X / 应配 人数+3”计数；初始值 = 服务端返回的当前 `board`。
    - “提交变更”按钮（把修改器草稿 `POST` 给 `set_board`）+ “开始游戏”按钮（`canStart` 时可用）。
  - 非房主：只读板子（无修改器）+ “等待房主开始…” 提示。
  - 状态区 `info` + 开始确认 `<dialog>`。
- **初始板子**：每个新房间狼人 2、村民 2，其余角色各 1。不读取板子缓存，公共板子始终显示服务器版本。
- **轮询**：`setInterval(2s) → POST /api/room_state/ {roomid,userid,userpsw}`（§0.1 唯一轮询端点）：
  - `phase='waiting'` 时 payload = `users` / `userCount` / `avatars` / `host` / `is_owner` / **`board`（当前 DB 模板）**。
  - **统一跳转判定（§0.1）**：`phase != 'waiting'`（例如变成 `'op'`）→ 按 phase 路由跳转（进 `/ops`）。`phase=='waiting'` → 用 payload 渲染本页（**非房主只读板子**）。
- **交互动作**：
  - 房主在修改器里调整份数（本地草稿，**尚未提交、不影响他人**）。
  - 点“提交变更” → `POST /api/set_board/ {board:{role:count}}`；**响应返回 DB 上已保存的 `board`（与轮询同一形状）**，房主用该返回值覆盖本地草稿和公共板子——保证修改器的数字与服务器一致（waiting 阶段后端不校验，允许半成品）。
  - 点“开始游戏”→ `<dialog>` 二次确认 → `POST /api/start_game/`：
    - **唯一校验边界**：Σ份数 != 人数+3 或非法 → 后端拒绝（`bad_board`），房间停留 waiting，`info` 显示错误。
    - 成功（`phase` 变 `'op'`）→ 按统一 phase 路由跳 `/ops`。
- **跳转**：按 §0.1 统一逻辑：`phase!=waiting → /ops`。

---

## 5. 对局三 View（`/ops`、`/reveal`、`/result`）

**对局轮询（三 View 与 waiting 共用同一个 `/api/room_state/`，套 §0.1 统一逻辑）**：`setInterval(2s) → POST /api/room_state/ {roomid,userid,userpsw}`。`mounted` 也先调一次。每次响应：
- 读 `phase`（`op|reveal|result`）。
- `phase` 与当前 View 不符 → `$router.push` 到 phase→View 对应路由。
- `phase` 与当前 View 相符 → 用该 phase 的 payload 渲染本页。

> 对局阶段 `phase` 同样来自同一个字段：`op`→`/ops`，`reveal`→`/reveal`，`result`（= 全员投完）→`/result`。任何刷新/断线都能靠它自动归位。

---

### 5.1 OperationView（`/ops`）—— 阶段一（15 秒操作）

**职责**：人人低头操作、不显示任何结果、倒计时收集选择。

- **组成元素**：
  - 顶部倒计时圈（15→0）+ 已提交人数 N/总人数。
  - 当前“正在操作的身份”操作界面（见身份伪装逻辑）。
  - 提交按钮 + `info`。
- **身份伪装逻辑**（服务端在 `phase='op'` 的 `/api/room_state/` 响应里下发 `role` 字段）：
  - 真身份有夜间行动（独狼/预言家/强盗/捣蛋鬼）→ 显示其操作界面（真捣蛋鬼看到“你是捣蛋鬼，选两张”）。
  - 真身份无需选择（有狼队友的狼人/爪牙/失眠者/村民）→ 服务端随机从模板中存在的可操作角色下发一个**假身份界面**，照常选（仅防场外，不参与结算）。
  - **阶段一不显示任何结果**：所选目标/中央牌一律背朝上，凭名字/位置点选。
- **轮询**：`setInterval(2s) → POST /api/room_state/ {roomid,userid,userpsw}`（§0.1 唯一端点）；`phase=op` 时 payload 为**提交同一套格式**：
  ```
  { phase:'op', role, my_choice, submitted, submitted_count, total_count, deadline_ms }
  ```
  - 用 `my_choice` 回显当前生效选择（丢包/重放也能恢复）。
  - 用 `submitted_count/total_count` 显示进度；`deadline_ms` 同步倒计时（本地计时为主，服务端兜底）。
  - **统一跳转判定（§0.1）**：`phase != 'op'`（变成 `reveal`）→ 按 phase 路由跳 `/reveal`。`phase=='op'` → 用 `my_choice` 等渲染本页（`/ops` 页的两态：匹配→渲染操作 UI，不符→跳走）。
- **交互动作**：
  - 每次选中 → `POST /api/night_action/ {choice}`；可多次改选，后者覆盖（best effort）。
  - 倒计时归零后（即使全员提前提交也等满）：服务端切换 `phase=reveal`（对始终未提交者随机默认操作）。
  - 倒计时到 0 而轮询仍 `phase=op` 时：本地强制提交默认/停止操作并继续轮询，等服务端推进。
- **跳转**：按 §0.1 统一逻辑：`phase≠op → /reveal`。

---

### 5.2 RevealView（`/reveal`）—— 阶段二（揭晓 + 投票）

**职责**：一次性拿到自己的揭晓结果，并在同一界面投出处决对象（一人一票）；轮询等全员投完。

- **组成元素**：
  - 你的初始身份卡（`role`）；若 `action_was_fake=true`，提示刚才是无实际效果的伪装操作。按真实身份分派的信息：
    - 狼人/爪牙：显示狼队友名单；爪牙提示“狼人不知道我是爪牙”。
    - 独狼：显示你窥视的那张中央牌。
    - 预言家：显示你看的玩家牌 / 两张中央牌。
    - 强盗：显示你换到的新身份（交换完成当时看到的牌，不代表最终身份）。
    - 捣蛋鬼：提示“你交换了 A 与 B”（不显示牌）。
    - 失眠者：显示复核后的自己的牌。
  - **投票控件**：所有玩家（含头像）+ 对每个玩家的“处决”按钮 + 一个“弃权”选项。
  - “我已投”提示 / 状态区 `info`。
- **进入时一次性拉取**：`mounted` 里 `POST /api/reveal/ {roomid,userid,userpsw}` **只调一次**，拿本玩家唯一正文应答（幂等，**不再轮询它**）。结果渲染到身份卡与信息区。
- **轮询**：`setInterval(2s) → POST /api/room_state/ {roomid,userid,userpsw}`。`phase='reveal'` 时 payload = `{voted}`（**仅投票进度**，不含揭晓内容）：
  - 用 `voted` 更新本人“已投票”状态，不展示他人投票进度。
  - **统一跳转判定（§0.1）**：`phase=='result'`（= 全员投完）→ 跳 `/result`。`phase=='reveal'` → 留在本页（此轮询**不是**再要揭晓结果）。
- **交互动作**：
  - 选中某人或弃权 → `POST /api/vote/ {target}`；**每人只允许投一次**（服务端按 `room.phase=='reveal'` 且本人未投判定，后续重投被拒）。
  - 投完后按钮置灰，等待其余玩家，靠轮询跳转。
- **跳转**：按 §0.1 统一逻辑：`phase=result → /result`。

---

### 5.3 ResultView（`/result`）—— 阶段三（结果揭示）

**职责**：全员投完后展示最终结果与历史。**无投票动作**。

- **组成元素**：
  - 胜负横幅：村民胜 / 狼人胜（含爪牙修正逻辑：无真狼时爪牙算狼，被投出则村民胜）。
  - 被投出处决者的最终身份（高亮）。
  - 所有人的最终身份卡（公开）。
  - 历史时间线：谁换了谁（强盗/捣蛋鬼）、预言家看谁、票型（每人投了谁/弃权）。
  - 返回主页按钮（**不提供“再来一局/回 WaitingRoom”**——一个房间只打一局，想再来请另建/另进一个房间）。
- **进入时**：`mounted` 里 `POST /api/result/ {roomid,userid,userpsw}` 一次，拿原始数据 `{center, players:[{userid, avatar, role, choice, vote_target}]}`，由前端计算最终身份、票数、胜负与行动回放后渲染。
- **轮询**：无（结果已定，一次性拉取即可）。
- **跳转**：手动回主页（**一个房间 = 一局**；本局结束后该房间不再复用，想开新局需新开房间或加入别的新房间）。

---

## 6. View 跳转 / 轮询总表

所有间歇轮询的 View（WaitingRoom / 三对局 View）统一轮询 **同一个 `/api/room_state/`**，套 §0.1：`phase` 与当前 View 不符 → 跳去 phase 对应 View；相符 → 用该 phase 的 payload 渲染本页。

| phase | 常驻 View | 轮询端点 | payload（相符时渲染） | phase 不符时的跳转 |
|---|---|---|---|---|
| `waiting` | WaitingRoom | `/api/room_state/` | `users, userCount, avatars, host, is_owner, board` | → 对应对局 View |
| `op` | OperationView | `/api/room_state/` | `role, my_choice, submitted, submitted_count, total_count, deadline_ms` | `≠op` → `/reveal` |
| `reveal` | RevealView | `/api/room_state/` | `voted` | `=result` → `/result` |
| `result` | ResultView | 无（进入前已在上一 View 等到全员投完） | — | 手动 |

（Home / CreateRoom / JoinRoom 无 phase 轮询，靠 POST 成功后手动一跳。一次性取数：`/api/reveal/` 阶段二进入时、`/api/result/` 结果界面进入时各拉一次，不走轮询。）

**关键不变**：所有轮询都指向同一个 `/api/room_state/`，每次都在做“**读 `phase` → 决定跳转或渲染**”；玩家刷新/断线也靠它自动归位。`phase`（waiting/op/reveal/result）共享同一字段、同一路由表、同一端点，仅“当前 View 渲染什么”不同。