# 一夜狼人 — 后端端点设计

## 1. 通用约定

- 除公开的 `GET /api/csrf/` 外，业务接口只接受 POST。
- 请求体必须是 JSON 对象；凭据 `{roomid, userid, userpsw}` 只放请求体。
- `roomid`：1–6 位字母数字；`userid`：1–7 位字母数字或下划线；`userpsw`：1–6 位字母数字。
- 业务响应为 `{ok: true, ...}` 或 `{ok: false, error: 英文错误码}`，HTTP 200。框架层的 CSRF 拒绝等仍使用对应 HTTP 状态。
- 非法 JSON 或字段类型返回 `bad_request`；不支持的方法返回 `method_not_allowed`。
- 房间不存在返回 `room_not_found`；需要认证的接口身份不匹配返回 `bad_credentials`；加入已有玩家时密码不匹配返回 `wrong_password`。
- 头像为服务端白名单名称，非法值回退默认头像；重新登录不更改原头像。

## 2. 最小存储

| 模型 | 持久化字段（除主键外） |
| --- | --- |
| Room | `roomid, phase, owner, board, center, op_start_time, created_at` |
| Player | `room, userid, userpsw, avatar, role, choice, vote_target` |

`role` 为初始牌；行动阶段仅向需要行动者返回真实操作身份，其他人返回 `role=null`，具体身份等揭晓时显示。

`choice={}` 表示未提交或无需行动；保存的真实操作仅包含输入字段，不含窥视结果、最终身份或狼队友。缺失的真实操作在截止时随机补全；无需行动者保持 `{}`。

`vote_target=null` 表示未投票，`""` 表示弃权，其他字符串为目标玩家。API 中的 `submitted / voted` 都是即时推导值，不是持久化字段。

等待期保存 `board`；发牌后清空，完整牌组可由初始牌推导。不存 `status / resolved_flag / ops / final_role / submitted / voted`。

开发期直接清空数据库重建，应用只保留一份初始迁移，不维护旧结构兼容。

## 3. 阶段与并发

`waiting → op → reveal → result`，一个房间只打一局。

- 没有后台计时线程；`room_state` 与 `night_action` 在请求中检查操作阶段是否到期。
- 需要行动者禁止提交跳过动作，未提交时获得随机默认操作；无需行动者只在前端点选，不提交。
- 即使全员已经提交，也必须等满时限。截止后拒绝写入新操作，返回当前阶段。
- 到期后，在事务中通过 `UPDATE Room SET phase='reveal' WHERE phase='op'` 取得唯一推进权，再补全默认操作。事务失败全部回滚，阶段条件保证只冻结一次。
- 加入、开始、夜间写操作和投票事务先锁房间，再检查权威状态。SQLite 用事务内第一条无值变化的 UPDATE 取得写锁，避免读后升级锁的竞争。
- 开始游戏在锁内重新统计人数、验证牌组、发牌；不会出现开局后加入却没有牌的玩家。
- 保存牌组带 `phase='waiting'` 条件，检查受影响行数，不能覆盖已开局房间。
- 投票带 `phase='reveal' AND vote_target IS NULL` 条件。最后一票在同一事务内进入结果阶段。

## 4. 端点

### GET `/api/csrf/`

公开，返回 `{ok: true, csrf_token}`，供后续请求的 `X-CSRFToken` 使用。

### POST `/api/create_room/`

请求 `{roomid, userid, userpsw, avatar}`。同一事务创建房间、房主玩家并关联所有者。

房号冲突（包括并发创建冲突）返回 `roomid_taken`。新房间固定初始板子：狼人 2、村民 2，其他已支持角色各 1（共 9 张），不随人数自动变化。

成功返回 `{ok: true, avatar}`。

### POST `/api/join_room/`

请求 `{roomid, userid, userpsw, avatar}`。

已有玩家校验密码并返回原头像；新玩家只允许加入等待中的房间，否则 `room_started`。同一用户名的并发加入只生成一个玩家。新玩家加入在房间锁内检查人数，已有 10 人返回 `room_full`；已有玩家仍可登录。

成功返回 `{ok: true, avatar}`。

### POST `/api/room_state/`

请求为凭据。检查阶段推进后，返回 `ok, phase` 和当前阶段的界面数据：

| phase | 数据 |
| --- | --- |
| waiting | `users:[{userid,avatar}], userCount, host, is_owner, board` |
| op | `role`（真实可操作身份；无需行动为 `null`）、`my_choice, submitted, submitted_count, total_count, deadline_ms, users` |
| reveal | `voted`（仅本人是否已投） |
| result | 无其他数据，结果正文另取 |

`deadline_ms` 是剩余毫秒数，不是时间戳。操作阶段另返回 `op_end_time_ms`（Unix 毫秒时间戳），前端据此持续显示剩余秒数与两位百分秒（如 `12.34`），归零后显示 `跳转中...` 并继续轮询等待阶段切换。操作阶段不返回任何身份观察结果或其他玩家操作。

### POST `/api/set_board/`

请求为凭据加 `board:{角色:数量}`。只允许等待阶段的房主。

角色必须合法，数量必须是非负整数（排除布尔值）；等待期允许总数不齐。成功返回 `{ok:true, board}`；失败为 `not_waiting / not_host / bad_board`。

前端增减只修改草稿，点击“提交板子”才保存。公共板子对房主和其他玩家均显示服务器已提交版本，不使用本地缓存。未提交或正在保存时不能开始；开始游戏不隐式保存草稿。

### POST `/api/start_game/`

请求为凭据。锁内检查房主、等待阶段、3–10 名玩家、总牌数为人数加三；强盗与捣蛋鬼各最多一张。

洗牌后保存各玩家初始牌和中央三张牌。预言家、强盗、捣蛋鬼和玩家中唯一的狼人执行真实操作；其余玩家无需行动，返回 `role=null`，只在前端随意点选。保留公共板子，记录开始时间，进入 `op`。

成功返回当前房间状态。失败为 `not_host / not_waiting / bad_players_count / bad_board`，不产生部分发牌。

### POST `/api/night_action/`

请求为凭据加 `choice`。验证真实可操作身份；无需行动者提交任何操作均返回 `bad_choice`。

| 展示身份 | 唯一允许的字段与目标 |
| --- | --- |
| seer | `{type:'seer', target:其他玩家}` 或 `{type:'seer', center_picks:[i,j]}` |
| robber | `{type:'robber', target:其他玩家}` |
| troublemaker | `{type:'troublemaker', target:其他玩家, target2:另一名其他玩家}` |
| werewolf | `{type:'wolf', target:'center_0'或'center_1'或'center_2'}`，类型别名 `werewolf` 也接受 |

中央索引必须为两个不同的整数，范围 0–2，不接受布尔值。拒绝多余字段、混合目标、主动跳过、窥视结果等客户端伪造数据，返回 `bad_choice`。

截止前允许多次提交，后者覆盖；截止后不再接受写入。阶段已变时返回真实阶段，不伪造 `op` 响应。

### POST `/api/reveal/`

请求为凭据，仅 `reveal` 阶段允许，否则 `not_in_reveal`。

返回 `{ok:true, phase:'reveal', role:初始身份, info, voted, users}`。`info` 根据初始牌和冻结的操作按需推导：

- 狼人：其他初始狼人；独狼另得选中的中央牌。
- 爪牙：全部初始狼人。
- 预言家：目标玩家初始牌或两张中央牌。
- 强盗：交换目标及交换完成当时得到的牌，不是最终身份。
- 捣蛋鬼：交换的两个目标，不给牌面。
- 失眠者：按强盗先、捣蛋鬼后的顺序推导最终身份。
- 村民：空对象。

不再返回 `action_was_fake`；掩护点选没有服务端记录。

仅结果阶段才能公开所有玩家的原始信息；揭晓阶段不能泄露他人原始操作或不属于自己的观察结果。

### POST `/api/vote/`

请求为凭据加 `target`。允许 `""` 弃权，不能投自己或房间外玩家。投票只能成功一次。

返回当前阶段和本人投票状态。失败为 `not_in_reveal / bad_target / already_voted`。

### POST `/api/result/`

请求为凭据，只允许 `result` 阶段，否则 `not_done`。

返回原始事实：

```json
{
  "ok": true,
  "phase": "result",
  "center": ["seer", "villager", "minion"],
  "players": [
    {"userid": "A", "avatar": "...", "role": "werewolf",
     "choice": {"type": "wolf", "target": "center_0"}, "vote_target": ""}
  ]
}
```

前端据此计算最终身份、票数、胜负、每人获胜状态及行动回放，不再由后端汇总或存储。

## 5. 前端结果规则

- 交换顺序：强盗 → 捣蛋鬼；无需行动者不参与交换。
- 唯一最高票者被处决，即使只有一票。
- 最高票多人并列：无人处决，并列者作为胜负判断的候选人。
- 最终玩家中有狼人：候选人中有狼人，好人胜；否则坏人胜。
- 无狼人但有爪牙：候选人中有爪牙，好人胜；否则坏人胜。
- 玩家中既无狼人也无爪牙：只有全员弃权时好人胜；只要有人投票（包括平票无人处决），全体玩家败。
- 全员弃权时没有候选人，零票玩家不算并列；玩家无坏人则好人胜，否则坏人胜。

## 6. 时长配置

操作时长统一读取 `onw_backend.config.OPS_DURATION`（`timedelta`），截止计算和写入条件使用同一配置。修改配置后重启服务生效。
