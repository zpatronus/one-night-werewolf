# 一夜狼人 — 后端端点设计（/api*）

> 配套文档：`design.md` 讲总体与结算；`view-design.md` 讲前端 View 流；本文**逐端点**记录后端 `/api*` 需要处理的**所有校验（checks）与操作（ops）**。
> 所有**带凭据**的端点一律 POST + JSON body（`roomid/userid/userpsw` 放 body，**绝不进 URL**）：哪怕是纯读的 `room_state` 也是 POST，因为凭据必须待在 body 里，GET 会逼它们进 query string = URL，违反「凭据不进 URL」不变式。
> 所有响应 `{"ok": bool, ...}` 一律 HTTP 200，靠 `ok` 判定，错误用**稳定英文 code**（前端 `gameConfig.js` 翻译）。
> GET 端点只有 `GET /api/csrf/`（公开，无凭据）。

---

## 0. 通用校验（每个需要凭据的端点都先走这套，通过才谈具体的 phase/权限校验）

所有 POST 端点**入口统一校验**，失败立即返回错误 code（不含任何泄露具体字段的成功数据）：

| # | 校验 | 失败 code |
|---|---|---|
| 0.1 | `roomid` 存在（`Room` 存在） | `room_not_found` |
| 0.2 | `userid` 在该房间内（`Player.room == room` 且 `userid` 匹配） | `bad_credentials` |
| 0.3 | `userpsw` 与该玩家匹配 | `wrong_password` |
| 0.4 | 输入形状校验：体必须是 JSON；缺失/类型错的必填字段同样按 0.x 归类 | `bad_request` |

> 前端不会主动发非法请求，但后端必须校验——**这是安全底线**。
> 需要额外「仅房主」「特定 phase」的端点，在各自小节再列附加校验。

---

## 0.5 阶段推进模型：**没有后台定时器 / 没有监控线程**（核心约定）

**没有任何东西在“盯着”15s 是否到点、谁没投**。所有阶段推进都由**到来的请求自身**触发——每个带凭据的 POST 处理器都同步地按这个骨架走：

```
handler(请求):
    1. 通用校验（§0）
    2. 本端点自己的校验 / 写操作（可能被允许、可能被拒绝）
    3. 阶段推进检查：读当前 phase，判断「推进条件」是否满足；满足则在同一请求内原子推进（§11）
    4. 返回当前 state
```

因此：

- `POST /api/room_state/` = **查当前 phase → 查是否满足推进条件 → 必要时更新 state → 返回**；
- `POST /api/night_action/` = **先执行本次写（可能允许、可能拒绝）→ 看能否推进 phase → 返回 state**。

**推论（为什么这样是对的）**：因为背后无人轮询，所以**当没有任何客户端发请求时，房间状态不会主动变化**——这完全没问题，因为我们此刻**没在向任何客户端展示任何东西**。状态只会在「有客户端来问的那一刻」才被推进。这与 HTTP 轮询天然兼容：总有一个客户端每 2s 来问一次，所以推进会及时发生。

各推进条件由**恰好先观察到它的那个请求**触发（用原子锁保证只推进一次，见 §11）：

- `op → reveal`：`now >= op_start_time + OPS_DURATION` **或** 全员已提交。任一打进 `room_state` 或 `night_action` 的调用方都可能先看到并触发。
- `reveal → result`：末尾一票在 `vote` 端点落库的**同一个请求**内同步推进。

- **校验**：无（公开，唯一没有凭据的端点）。
- **操作**：返回当前会话的 CSRF token。前端 `api.js` 的 `ensureToken()` 惰性拉取一次并缓存，之后所有 POST 带 `X-CSRFToken` 头。
- **响应**：`{"csrfToken": "..."}`。

---

## 2. `POST /api/create_room/` — 建房 + 创建房主

- **Body**：`{roomid, userid, userpsw, avatar}`。
- **附加校验（顺序）**：
  - 2.1 `roomid` 长度 ≤6、仅字母/数字。若已存在 → `roomid_taken`。
  - 2.2 `userid` 长度 ≤7、仅字母/数字/`_`；`userpsw` 长度 ≤6、仅字母/数字。（命中则 `bad_request`）
  - 2.3 `avatar` 必须是**已允许的合法头像文件名**（服务端白名单，杜绝任意路径/外链）→ 否则回退默认头像。
- **操作**（单一事务，原子）：
  - 创建 `Room {roomid, status='waiting', phase='waiting', owner=NULL, board=默认模板, center=[]}`。
  - 创建 `Player {room, userid, userpsw, avatar, role=NULL, ...}`，并把 `room.owner` 设为该玩家（**创建者即房主**）。
  - 用该房间的默认模板初始化 `room.board`（Σ 可能不是「人数+3」，waiting 阶段允许非法，见 design §6.6）。
- **响应**：`{"ok": true, "avatar": "<权威头像文件名>"}`（后端权威头像回传，前端 `setMyAvatar`）。
- **错误 code**：`roomid_taken`、（格式类）`bad_request`。

---

## 3. `POST /api/join_room/` — 加入房间 / 登录已有玩家

- **Body**：`{roomid, userid, userpsw, avatar}`。
- **附加校验**：
  - 3.1 `roomid` 存在（否则 `room_not_found`）；房间处于 `waiting` 才能**新加入**。
  - 3.2 玩家不存在 → 创建新玩家（`created=true`）；玩家已存在 → 校验密码（错 → `wrong_password`）。
  - 3.3 已有玩家保持其**首次选定的头像**（服务端权威），忽略本次 `avatar`。
- **操作**：
  - 新玩家：在房间 `waiting` 阶段 `create_or_get` 一个 `Player`，写入提供/默认的头像。
  - 老玩家：只校验+返回，不改头像、不改房间状态。
- **响应**：`{"ok": true, "created": true|false, "avatar": "<权威头像>"}`。
- **错误 code**：`room_not_found` / `wrong_password` / `room_started`（已开局想当新玩家加入）。

---

## 4. `POST /api/room_state/` — **唯一轮询端点**（读）

所有间歇轮询（waiting + 三对局 View）**只打这一个端点**，前端按 `phase` 决定跳转或渲染（view-design §0.1）。它**承担了房间路由的职责**：Create/Join 成功后前端直接进 `/waitingroom`，任何 `phase != waiting` 都靠这里的 `phase` 字段自动归位到对应 View —— 因此**不需要单独的 `/api/room_status/`**。

- **校验**：§0 通用校验通过即可；**不按本人 phase 拒绝**（相反——它要驱动跳转，任何 phase 都该能读到）。
- **操作（§0.5 骨架第 3 步也在此执行）**：先做一次**推进检查**（`op→reveal` 或 `reveal→result` 条件满足就同步推进，§11），再按推进后的当前 `phase` 返回不同 payload：

| `phase` | 返回 payload |
|---|---|
| `waiting` | `users`（房间内用户名列表）、`userCount`、`avatars`（`{userid: avatarFile}`）、`host`（房主 userid）、`is_owner`（当前玩家是否房主）、`board`（DB 上 `{role:count}`） |
| `op` | `role`（当前玩家“正在操作的身份”）、`my_choice`（当前生效操作，回显用）、`submitted`、`submitted_count`、`total_count`、`deadline_ms` |
| `reveal` | `voted`（本人是否已投）、`voted_count`、`total_count`（**仅投票进度**，不含阶段一/揭晓内容） |
| `result` | 空（结果由 `/api/result/` 一次性给） |

- **`op` 的 `deadline_ms` 计算**：`deadline = room.op_start_time + OPS_DURATION`，`deadline_ms = deadline - now`。**`OPS_DURATION` 见 §12（`is-dev-machine` 文件存在时 60s，否则 15s）**。
- **响应**：`{"ok": true, "phase": "op", ...该 phase payload}`。

---

## 5. `POST /api/set_board/` — 房主配置板子（waiting 阶段）

- **Body**：`{roomid, userid, userpsw, board: {role_code: count}}`。
- **附加校验**：
  - 5.1 当前玩家是房主（`room.owner == this player`）→ 否则 `not_host`。
  - 5.2 房间 `phase == 'waiting'` → 否则 `not_waiting`。
  - 5.3 `board` 形状合法：键都是合法角色 code 集合的子集、值都是非负整数。**waiting 阶段不校验总数**（房主可能正编辑到一半，Σ≠人数+3 允许）。
- **操作**：把 `board` **整体覆盖保存**到 `room.board`（DB 唯一真值来源）。
- **响应**：**回传 DB 上刚保存的 `board`**（与 `/api/room_state/`@waiting 同形状），房主用返回值覆盖本地草稿并写回 `localStorage['board:<人数>']`。
  `{"ok": true, "board": {role_code: count}}`。
- **错误 code**：`not_host` / `not_waiting` / `bad_board`。

---

## 6. `POST /api/start_game/` — 房主开始游戏（**唯一校验边界**）

- **Body**：`{roomid, userid, userpsw}`。
- **附加校验**：
  - 6.1 房主 → `not_host`。
  - 6.2 `phase == 'waiting'` → `not_waiting`。
  - 6.3 **玩家人数合法**：玩家数在 [3, 10] 内（含）→ `bad_players_count`。
  - 6.4 **板子合法性**（唯一校验边界，waiting 阶段允许非法就在这收口）：读 DB 上 `room.board`，校验——
    - 每种计数都是**非负整数**；
    - **Σ计数 == 玩家人数 + 3**（每名玩家 1 张 + 中央 3 张）；
    - 各角色 in 合法角色集合。
    - 任一不满足 → `bad_board`，**房间停留 waiting，回滚，不发牌**。
- **操作**（**单一事务、原子**，成功后房间进入阶段一）：
  - 用 `room.board` 摊开一副牌（`players+3` 张），洗牌；
  - 每人发 1 张 → `role`（初始身份）；剩 3 张 → `room.center`；
  - 为每个无夜间行动的玩家（狼群狼/爪牙/失眠者/村民）**随机下发一个假身份**（从 `{seer, robber, troublemaker, lone-wolf}` 取，view-design §5.1），仅作为 `phase='op'` 时 `role` 字段展示、不参与结算；
  - 记录 `room.op_start_time = now`、`room.resolved_flag = False`；
  - `room.phase = 'op'`。
- **响应**：`{"ok": true, "phase": "op", "deadline_ms": ...}`（立即给前端的倒计时；`deadline_ms` 用 §12 的 `OPS_DURATION` 算）。
- **错误 code**：`not_host` / `not_waiting` / `bad_players_count` / `bad_board`。

---

## 7. `POST /api/night_action/` — 阶段一提交操作（写）

- **Body**：`{roomid, userid, userpsw, choice: {type, target, target2, center_picks}}`。
- **附加校验**：
  - 7.1 `phase == 'op'`（**DB 条件写的前置**）→ 否则 `not_in_op`。
  - 7.2 `choice` 形状与本人“正在操作的身份”匹配（该身份要求几个目标、是否选中央牌）→ 不匹配 `bad_choice`（best effort，宽松即可）。
- **操作**（**DB 条件写保证原子**）：
  - `UPDATE player SET choice=?, submitted=TRUE WHERE id=<player> AND room.phase='op'`；
  - **按受影响行数判定**：返回 0 行 = 房间已离开 `op`，此迟到写直接忽略（返回当前 `phase`，让前端去跳转）。
  - 允许多次提交、后者覆盖（best effort）。
  - 写完后再按 §0.5 骨架第 3 步做一次**推进检查**（若现在全员已提交或已超时 → 触发 `op→reveal`，§11），再返回。
- **响应**：与 `phase='op'` 的 `/api/room_state/` **同格式**（`{ok, phase, role, my_choice, submitted, submitted_count, total_count, deadline_ms}`）——提交丢了下次轮询能把 `my_choice` 回显出来，重交即可。
- **错误 code**：`not_in_op` / `bad_choice`。

---

## 8. `POST /api/reveal/` — 阶段二揭晓（**一次性、幂等**，不轮询）

- **Body**：`{roomid, userid, userpsw}`。
- **附加校验**：`phase == 'reveal'` 才返回正文；仍未到 → `not_yet`（前端轮询 `/api/room_state/` 等 `phase=reveal` 再来）。
- **操作**：
  - 若上一次轮询已触发结算但玩家还没拿到正文，这里幂等重算/读取该玩家的 reveal 记录（不重复结算）。
  - 返回本人**唯一正文应答**，按身份分派（与 view-design §5.2 一致）：
    - 狼人/爪牙：狼队友名单（爪牙另提示“狼人不知道我是爪牙”）；
    - 独狼：窥视的那张中央牌；
    - 预言家：看的玩家牌 / 两张中央牌；
    - 强盗：换到的新身份（即时 `final_role`）；
    - 捣蛋鬼：提示“交换了 A 与 B”（不显示牌）；
    - 失眠者：复核后的自己的牌。
  - 同时返回该玩家的 `final_role` + 当前有多少人已投 `voted_count`（可选，辅助）。
- **响应**：`{"ok": true, "final_role": "...", "detail": {...分派信息}}`。
- **错误 code**：`not_yet` /（通用）`bad_credentials`。

---

## 9. `POST /api/vote/` — 阶段二投票（一人一票）

- **Body**：`{roomid, userid, userpsw, target}`（`target` 为被处决玩家 userid，或 `""` 弃权）。
- **附加校验**：
  - 9.1 `phase == 'reveal'`（DB 条件写前置）→ `not_in_reveal`。
  - 9.2 本人尚未投过 → `already_voted`（**改投/重投被拒**，`voted` 恒为单次信号）。
  - 9.3 `target` 为空串（弃权）或属于房间内玩家 → `bad_target`。
- **操作**（**DB 条件写**）：`UPDATE player SET vote_target=?, voted=TRUE WHERE id=<player> AND room.phase='reveal' AND voted=FALSE`；受影响行数 0 → 拒绝。
- **最后一名玩家投票落库**后，服务端在**同一事务**内把 `room.phase` 推进到 `result`。
- **响应**：`{"ok": true, "phase": "reveal" | "result", voted_count, total_count}`。
- **错误 code**：`not_in_reveal` / `already_voted` / `bad_target`。

---

## 10. `POST /api/result/` — 阶段三最终结果（一次性）

- **Body**：`{roomid, userid, userpsw}`。
- **附加校验**：`phase == 'result'`（全员已投完）→ 否则 `not_done`。
- **操作**：只读，聚合本局最终数据：
  - 被投出处决者 + 其**最终身份**；
  - 所有人的最终身份卡（公开）；
  - 胜负（design §1.2：含爪牙修正——场上无真狼且爪牙被投 → 村民胜）；
  - 历史时间线（谁与谁交换、预言家看谁、每人票型）。
- **响应**：`{"ok": true, "executed": {userid, final_role}, "players": [{userid, final_role}], "win": "good"|"evil", "history": [...]}`。
- **错误 code**：`not_done`。

---

## 11. 阶段一结算触发（`resolver`）— 请求驱动 + 并发安全

**没有线程、没有定时器**（§0.5）。由“最后一名玩家提交”或“倒计时归零”时**恰好先观察到该条件的那个请求**触发——`/api/room_state/`、`/api/night_action/`、`/api/reveal/` 都会在骨架第 3 步执行同样的推进检查并尝试触发。没有客户端来问，就什么都不会做：

- 用 `transaction.atomic` + `room.resolved_flag` 保证**只结算一次**（first-write 拿锁，SQLite 首条写拿排他锁，与阿瓦隆 `vote` 一致）。
- **结束条件**：`now >= op_start_time + OPS_DURATION`（§12）**或** `submitted_count == total_count`。
- **结算顺序（严格）**：狼人/爪牙互认 → 独狼看中央 → 预言家 → **强盗先抢 → 捣蛋鬼再换 → 失眠者最后复核**。每个玩家的 `final_role` 以交换后的牌为准。
- **未提交者**：服务端为ta**随机指定默认操作**（`submitted` 仍为 False），随正常操作一起结算（best effort）。
- **整个 `op→reveal` 在单个事务内完成**：快照最终操作 → 结算 → 生成每人的 reveal 记录 → 写死 `room.phase='reveal'`。事务提交前阶段一写仍可见；提交后一律被拒（`UPDATE ... WHERE phase='op'` 返回 0 行）。
- `phase='reveal'` 后**所有** `/api/night_action/` 迟到写被忽略。

---

## 12. `is-dev-machine` — 阶段一时长开关（区分开发/生产）

后端在**单个标记文件**存在与否来决定 `OPS_DURATION`：

- **检测**：顺序查找项目基线目录下的 `is-dev-machine` 文件（`os.path.exists(<PROJECT_ROOT>/is-dev-machine)`）。只认“存在”与否，内容不读。
- **规则**：文件存在 → `OPS_DURATION = 60`（开发时给足操作时间）；不存在 → `OPS_DURATION = 15`（线上正常 15 秒）。
- **生效点**：所有用到“15 秒”的地方统一走 `OPS_DURATION`——
  - `POST /api/start_game/` 设置 `room.op_start_time` 与返回的 `deadline_ms`；
  - `POST /api/room_state/`@op 的 `deadline_ms`；
  - `resolver` 判断倒计时是否归零。
- 该文件路径与开关应集中在 `onw_backend/config.py`（如 `OPS_DURATION = 60 if (BASE_DIR/"is-dev-machine").exists() else 15`），**别在多个端点里重复拼路径**。`.gitignore` 应包含 `is-dev-machine`（它属于某台机器的本地标记，不进版本库）。

---

## 13. 端点 × 校验/操作总表

| Endpoint | 通用校验 | 附加校验 | 关键操作 | 错误 code |
|---|---|---|---|---|
| `GET /api/csrf/` | — | — | 返回 CSRF token | — |
| `POST /api/create_room/` | roomid 存在与否判定 | 格式 / not taken / avatar 白名单 | 建房 + 建房主 | `roomid_taken`, `bad_request` |
| `POST /api/join_room/` | 房间存在 | waiting 才能新加入 / 密码 | create-else-login，权威头像 | `wrong_password`, `room_started`, `room_not_found` |
| `POST /api/room_state/` | 凭据 | 不拒 phase（驱动跳转 + 路由） | 只读，按 phase 返回 payload | `bad_credentials` |
| `POST /api/set_board/` | 凭据 | 房主 / waiting / board 形状 | 整体覆盖 `room.board`，回读 | `not_host`, `not_waiting`, `bad_board` |
| `POST /api/start_game/` | 凭据 | 房主 / waiting / 人数 / **板子合法性** | 发牌 + 随机假身份 + `phase=op` | `not_host`, `not_waiting`, `bad_players_count`, `bad_board` |
| `POST /api/night_action/` | 凭据 | `phase=op` / choice 形状 | **DB 条件写** choice | `not_in_op`, `bad_choice` |
| `POST /api/reveal/` | 凭据 | `phase=reveal` | 幂等返回本人揭晓正文 | `not_yet` |
| `POST /api/vote/` | 凭据 | `phase=reveal` / 未投 / target 合法 | **DB 条件写** vote，末票推进 result | `not_in_reveal`, `already_voted`, `bad_target` |
| `POST /api/result/` | 凭据 | `phase=result` | 只读最终结算/胜负/历史 | `not_done` |

> 阶段一结算触发（§11）不属于独立端点，而是挂在任一调用方的内部原子流程。