# If you're an AI agent, read the view-design.md and endpoint-design.md instead

> 当前数据结构、请求字段与并发约束以 [endpoint-design.md](endpoint-design.md) 为准；使用本项目自定义胜负规则。
>
> 最新约定：新房间固定 9 张初始模板（狼人 2、村民 2、其他角色各 1）；加入最多 10 人。板子增减只编辑草稿，显式提交后才更新公共板子，不读本地板子缓存。无需行动者（包括多人狼）收到 `role=null`，前端明确提示无需操作并提供本地点选按钮，不提交、不保存；仅独狼执行真实窥视。下文旧版示例若不一致，以本约定和端点文档为准。


# 一夜狼人 (One-Night Werewolf) — 设计文档

> 目标：复刻 [God of Avalon](https://github.com/zpatronus) 的**基础设施**（房间/用户名/密码/头像、路由、CSRF、轮询等）保持**一模一样**，在其上实现一个《一夜狼人》的对局逻辑。
> 技术栈：**前端 Vue 3** + **后端 Django 5** + **`uv` 管理依赖**。实时性不需要 websocket，统一使用**健壮的 HTTP 请求轮询**。

---

## 0. 核心设计思想（先读这段）

一夜狼人最关键的难点，在于**夜间信息**与**场外信息（作弊）**的控制。本设计用“三个独立 View + 强制 15 秒同时操作”解决：

1. **第一轮（操作阶段）所有人必须低头操作 15 秒——无一例外。**
   每个人在阶段一都要点屏幕，**哪怕是失眠者、村民**这类夜间没有真实操作的纯视觉身份。界面明确提示“你的身份夜间无需操作”，提供可随意点选的按钮以减少动作泄露；这些选择只存在于前端。
   这样，桌面观察者无法通过“谁在玩手机 / 谁没在玩”来推断谁是有身份的——**杜绝了场外信息**。

2. **所有人同时操作，但服务端结算有严格顺序。**
   虽然大家一起按，但真正的夜间结算必须是：**强盗先抢，捣蛋鬼再换**，最后失眠者复核。因为有这个顺序，交换结果才是确定的。

3. **操作完成后统一揭晓，然后接着投票。**
   阶段一里每个人都能看到自己**正在操作的身份**，并做出**有真实身份依据的选择**——真捣蛋鬼在阶段一就被告知“你是捣蛋鬼，请选两张”，真预言家被告知去看谁；但**阶段一不显示任何“结果”**：看不到你窥视到的牌面、看不到换牌后的牌面，只是做选择。真实身份与行动结果**全部在第二个 View（阶段二）揭晓**——预言家看到他阶段一选的牌、捣蛋鬼看到自己确实换了牌、村民这才得知自己是村民；**同一阶段二界面里就给出投出处决对象的控件（每人只能投一次）**。全员投完后，第三 View 展示最终结果。

> 一句话：**外面看起来人人都在低头操作（防作弊），每个人按自己看到的身份做出真实选择、但都不见结果；服务端按真实身份 + 指定顺序结算，阶段二统一揭晓并投票，阶段三揭晓结果（保正确）。**

---

## 1. 游戏规则摘要

### 1.1 角色与阵营

| 角色 code      | 名称    | 阵营 | 夜间能力                                   | 真实夜间行动（阶段一选目标，结果阶段二揭晓） |
| -------------- | ------- | ---- | ------------------------------------------ | -------------------------------------------- |
| `werewolf`     | 狼人🐺   | 狼人 | 与同伴互认；**独狼**可看中央 3 张中的 1 张 | 独狼：选看哪张中央牌                         |
| `minion`       | 爪牙💀   | 狼人 | 看狼人是谁（不告诉狼人自己）               | 无（阶段一提供本地点选按钮）           |
| `seer`         | 预言家🔮 | 村民 | 看 1 名玩家的牌，**或**看中央 2 张牌       | 选看哪人 / 哪两张中央                        |
| `robber`       | 强盗🥷   | 村民 | 与 1 名玩家换牌，换后看自己的新牌          | 选与谁换                                     |
| `troublemaker` | 捣蛋鬼🃏 | 村民 | 交换另外两名玩家的牌（不看牌、不换自己）   | 选要交换哪两人                               |
| `insomniac`    | 失眠者🌙 | 村民 | 结算**最后**再确认一次自己的牌             | 无（阶段一提供本地点选按钮）           |
| `villager`     | 村民👤   | 村民 | 无                                         | 无（阶段一提供本地点选按钮）           |

### 1.2 获胜条件（自定义规则，按最终身份）

- 每人投其他一名玩家或弃权，不能投自己；投票不可修改。
- 唯一最高票者被处决，即使最高只有一票。
- 最高票多人并列时无人处决，但这些并列者作为胜负判断的候选人。
- 玩家中存在狼人：候选人中有狼人则好人胜，否则坏人胜。
- 玩家中没有狼人但有爪牙：候选人中有爪牙则好人胜，否则坏人胜。
- 玩家中既无狼人也无爪牙：只有全员弃权时好人胜；只要有人投票（即使平票无人处决），全体玩家败。
- 全员弃权时没有候选人，零票玩家不算并列；无坏人则好人胜，否则坏人胜。


---

## 2. 页面 / 路由总览

| 路由           | View              | 说明                                                                | 参考资料                                |
| -------------- | ----------------- | ------------------------------------------------------------------- | --------------------------------------- |
| `/`            | `HomeView`        | 主页 + 玩法介绍 + 更新日志                                          | 与阿瓦隆 `HomeView.vue` 一模一样        |
| `/createroom`  | `CreateRoomView`  | 房间ID + 用户名 + 密码 + 头像；**创建者即房主**                     | 与阿瓦隆 Create/Join 合并体的改造版     |
| `/joinroom`    | `JoinRoomView`    | 房间ID + 用户名 + 密码 + 头像（加入/登录已有玩家）                  | 与阿瓦隆 `JoinRoomView.vue` 一模一样    |
| `/waitingroom` | `WaitingRoomView` | 房间玩家列表；**房主可配置板子并开始**；非房主只读并等待            | 阿瓦隆 `WaitingRoomView.vue` + 板子配置 |
| `/ops`         | `OperationView`   | **阶段一**：15s 操作（所有人低头操作）                              | 新增（对局三视图之一）                  |
| `/reveal`      | `RevealView`      | **阶段二**：一次性揭晓真实身份与操作结果 + 提供投票控件（一人一票） | 新增                                    |
| `/result`      | `ResultView`      | **阶段三**：全员投完后的结果揭示                                    | 新增                                    |

> 对局的三阶段坚持写成 **3 个独立 View**（`/ops`、`/reveal`、`/result`），由服务端 `room_state` 的 `phase` 字段驱动进入哪个 View；前端每 2s 轮询 `room_state` 自动跳转，与阿瓦隆 waiting→inroom 的跳转方式完全一致。投票动作发生在阶段二（`/reveal`）界面内。

---

## 3. 基础设施（与阿瓦隆一模一样）

以下模块在规则上不做任何改动，直接沿用阿瓦隆的实现模式，保证“一模一样”：

### 3.1 前端基础设施

- `src/main.js`：`createApp` + `router` + `store`。
- `src/store/index.js`：Vuex，含 `state.server`（后端地址，不含尾斜杠）与 `state.base`（**站点 URL 前缀**，nginx 挂在子路径时用，默认 `''`）。
- `src/api.js`：`ensureToken()` 惰性拉取 CSRF 一次 + `post(path, body)`（凭据放 JSON body，绝不进 URL）+ `get(path)`；统一 `withCredentials`。**所有请求 URL 都拼成 `${base}${path}`**——`path` 约定以 `/api/` 开头，`base` 为站点的 URL 前缀（nginx 把前端与后端一起挂在某个子路径下时，由 `base` 补上，`/` 部署时 `base=''`）。
- `src/avatar.js`：头像身份 = **文件名**；`localStorage` 缓存选中文件（键 `avatar`）+ 每个 SVG 内容缓存（`avatarFile:<name>`）`AVATARS` 稳定排序 + `randomAvatar/getMyAvatar/setMyAvatar/avatarUrl`。头像 `<img>` 的 `src` 同样经 `${base}${server}/...` 拼接以适配前缀。
- `src/playerOrder.js`：基于 `(roomId, username)` 的稳定哈希排序，保证对局内展示顺序一致。
- `src/App.vue`：masthead + 顶部 nav + 全局 SCSS 设计变量（`--good`/`--evil`/`--accent` 等）。新增一夜间角色配色（见 §7）。
- `src/router/index.js`：注册上述 7 个路由；**使用 `createWebHistory(import.meta.env.BASE_URL)`**，目的地在 URL 前缀下仍能正确解析（Vue3 路由 base 与前端 `vite base`/nginx 前缀保持一致）。

> **nginx 子路径部署（前缀支持）**：整体站点（前端 Vue + 后端 Django `/api/`）可能被挂在某个子路径下（如 `https://host/onw/`）。前后端统一约定——**前端 `base`（含 `router createWebHistory` 的 base、`api.js`/`avatar.js` 的请求前缀）与后端 `ROOT_URLCONF` 里的站内前缀都由同一份配置驱动**：要么 nginx 不剥前缀、后端 URLconf 直接含该前缀，要么 nginx 剥掉前缀只转发 `/api/...` 给 Django；两种皆可，只要前后端对“前缀到哪为止”的认知一致。所有 API 一律相对引用（经 `${base}` 拼出的绝对路径），同一站点下前后端天然同源，无 CORS。`state.base` 与 `config` 的 `URL_PREFIX` 就负责提供这一份一致的前缀。

### 3.2 后端基础设施

- Django project `onw_backend`，app `room`。
- `room/models.py`：`Room`/`Player`（扩展见 §6）。
- `goa_backend/config.py`：`DEBUG/SECRET_KEY/BACKEND_URLs/FRONTEND_URLs`、`URL_PREFIX`（站内前缀，见 §3.1），**gitignore**；附 `config-sample.py`。
- 所有读秘密/改状态接口均为 **POST + JSON body `{roomid, userid, userpsw}`**；所有响应 `{"ok": bool, ...}` 一律 200，靠 `ok` 判断；错误用**稳定英文错误码**，前端 `gameConfig.js` 翻译。
- CSRF：`/api/csrf/` 取 token；前端 `X-CSRFToken`。
- CORS/CSRF_TRUSTED：`django-cors-headers` + 来自 config。
- 管理命令：`delete_old_rooms`（按日期清理）、`reset_db`（备份 + 重建空库）。
- 迁移/部署：`./scripts/migrate_db.sh`（先备份再重建，无向后兼容）。

### 3.3 差异点（唯一允许的改动）

- **依赖管理用 `uv`**：以 `pyproject.toml` + `uv.lock` 管理（阿瓦隆是 pip + requirements.txt）。命令形态：`uv sync`、`uv run python manage.py migrate`、`uv run python manage.py runserver`。
- **创建房间也带身份**：`/api/create_room/` 直接创建「房间 + 房主玩家」，无需再走一次 join；见 §4.2。

---

## 4. 基础设施页面逐页说明

### 4.1 HomeView（`/`）

与阿瓦隆完全相同：玩法介绍、`--help` 说明、更新日志、页脚。文案改为一夜狼人。无新逻辑。

### 4.2 CreateRoomView（`/createroom`）

**与阿瓦隆最大的区别：创建房间也要带用户名 + 密码 + 头像，且创建者默认成为房主。**

- **房间ID**：复用阿瓦隆 `checkRoomId`（≤6 位，仅字母/数字）+ “下一个”按钮生成器 + `localStorage 'roomId'` 记忆。
- **玩家ID**：复用 `checkUserId`（≤7 位，字母/数字/`_`），`localStorage 'userId'` 记忆。
- **玩家密码**：复用 `checkUserPsw`（≤6 位，字母/数字）+ 随机按钮，`localStorage 'userPsw'` 记忆。
- **选择头像**：完全复用阿瓦隆的 `<dialog>` 头像选择器（`avatar.js`，首个头像永久化，后端返回权威文件名）。
- **提交**：`POST /api/create_room/ {roomid, userid, userpsw, avatar}`。成功后后端已创建房间并使当前玩家成为 `owner`，跳转到 `/waitingroom`。

> 之所以这里带上身份，是因为一夜狼人没有阿瓦隆那种“先建房号、再另立玩家”的松散结构——房主本身就是最后一个能开始游戏的人，身份必须从创建那一刻绑定。

### 4.3 JoinRoomView（`/joinroom`）

与阿瓦隆 `JoinRoomView.vue` **一模一样**：

- 房间ID + 玩家ID + 玩家密码 + 头像选择（复用同一套校验与 localStorage 记忆、头像 `<dialog>`）。
- 已有玩家则校验密码登录（返回权威头像）；未注册则新建玩家。
- 成功后直接跳 `/waitingroom`：不再额外查房间状态——房间若已开局，`/api/room_state/` 统一轮询会立刻发现 `phase != waiting` 并把玩家归位到对应对局 View。
- 顶部保留阿瓦隆的“个人密码非房间密码、明文传输、建议随机”等 Tips。

---

## 5. WaitingRoomView（`/waitingroom`）

沿用阿瓦隆的整体布局与 2s 轮询 `updateRoomInfo` 模式，**新增房主板子配置能力**。

### 5.1 布局

- 信息卡：房间ID / 你的玩家ID / 玩家数量。
- “房间内的玩家”卡片网格（头像 + 名字，`playerOrder.sortPlayers` 稳定排序）。
- **板子**区块：展示当前 `board:<人数>` 模板（见 §6.3）。
- 房主专属：**板子配置区** + “开始游戏”按钮；非房主只读展示、等待。

### 5.2 板子配置（房主）

- 房主（后端 `is_owner`）可以为**当前人数对应的整副牌组**设置**每种角色的份数**，即一个 `{role_code: count}` 映射——例如 `{"werewolf":2, "seer":1, "robber":1, "troublemaker":1, "insomniac":1, "minion":0, "villager":?}`。每种角色都用加减的份数步进控件调整，`0` = 不下这张牌。
- **总数提示**：配置区实时显示「已配 香牌数 ／ 应配 玩家人数+3」，帮助房主配齐；但 waiting 阶段**允许配不齐/非法**（房主编辑中），后端只存不校验。
- **配置缓存到 `localStorage`，以人数为 key**：键 `board:5`、`board:6` … `board:10`（值为该人数对应的 `{role:count}` 映射）。切换人数或返回重进，自动加载上次该人数的配置。
- 配置下发：`POST /api/set_board/ {roomid, userid, userpsw, board:{role_code: count}}`（仅房主有效）。waiting 阶段后端只保存该映射，不校验合法性。
- 开始游戏：`POST /api/start_game/`（仅房主）。这是**唯一校验边界**：后端在推进到 `phase=op` 前校验「各角色份数均非负且 **Σ计数 == 玩家人数 + 3** 且构成合法」，非法则拒绝开始、房间停留 waiting（见 §6.6）。校验通过才跳 `/ops`。

### 5.3 数据

`phase='waiting'` 时的 `POST /api/room_state/` 返回：`users`（房间内玩家）、`userCount`、`avatars`、`host`（房主 userid）、`is_owner`（当前玩家是否房主）、`board`（后端已保存的 `{role:count}` 份数映射）。前端据此决定显示配置 UI 还是只读。

---

## 6. 后端设计

### 6.1 最小持久化模型

`Room` 保存：`roomid`、`phase`、`owner`、等待期的 `board`、中央初始牌 `center`、`op_start_time`、`created_at`。

`Player` 保存：`room`、`userid`、`userpsw`、`avatar`、初始身份 `role`、原始操作 `choice`、原始投票 `vote_target`。

`choice={}` 表示未提交或无需行动；保存的真实操作仅包含输入字段，不含窥视结果、最终身份或狼队友。缺失的真实操作在截止时随机补全；无需行动者保持 `{}`。
- `vote_target=null` 表示未投；`""` 表示弃权；其他值为被投玩家 ID。
- 行动阶段按初始牌与狼人数量推导可操作身份；无需行动者返回 `role=null`。
- 发牌后 `board` 清空，完整牌组可由玩家初始牌和中央牌推导。
- 不持久化 `status`、`resolved_flag`、`ops`、`final_role`、`submitted`、`voted`，也不在 `choice` 里保存窥视结果、狼队友或强盗换到的牌。
- API 为界面临时计算 `submitted`、`voted`；这些不是数据库字段。
- 开发期直接重建数据库，仅保留一份初始迁移，不维护旧结构兼容。

### 6.2 行动冻结与信息推导

需要行动者必须选择，未提交时由服务端随机补全；无需行动者仅在前端随意点选，不提交操作。必须等待完整操作时限，截止后拒绝新增或覆盖操作。

服务端在事务中通过 `UPDATE Room ... WHERE phase='op'` 取得阶段推进权，补全默认操作并进入 `reveal`。只有一个请求能够完成这次转换，不需要额外的结算标记。

初始牌和冻结后的操作足以推导信息：

1. 狼人互认、爪牙看狼人：读取玩家初始身份。
2. 独狼：读取选中的中央初始牌；狼群的中央选择不生效。
3. 预言家：读取另一玩家初始牌，或两张不同中央初始牌。
4. 强盗：与所选玩家交换；其观察结果是该玩家初始牌。
5. 捣蛋鬼：在强盗之后交换其他两名玩家的牌。
6. 失眠者：根据以上交换计算自己的最终身份。

揭晓接口只返回当前玩家有权知道的信息，不能返回其他人的原始行动或全体最终牌。结果阶段所有信息公开，接口仅返回 `center` 和各玩家 `{userid, avatar, role, choice, vote_target}`；前端计算最终身份、票数、胜负和回放。

### 6.3 板子模板（默认可配置）

板子是一张 `{role_code: count}` 的**份数映射**，代表整副牌组；**总牌数 = 玩家人数 + 3 张中央牌** = 每位玩家 1 张 + 中央 3 张。房主可自由设置每种角色的份数。下面是各人数的默认份数映射（`villager` 份数 = 总牌数 − 其它角色份数）：

| 人数 | 默认板子 `{role: count}`                                                                |
| ---- | --------------------------------------------------------------------------------------- |
| 3    | `werewolf:1, seer:1, robber:1, troublemaker:1, insomniac:1, villager:1`（共 6 = 3+3）   |
| 4    | `werewolf:2, seer:1, robber:1, troublemaker:1, insomniac:1, villager:1`（共 7 = 4+3）   |
| 5    | `werewolf:2, seer:1, robber:1, troublemaker:1, insomniac:1, villager:2`（共 8 = 5+3）   |
| 6    | `werewolf:2, seer:1, robber:1, troublemaker:1, insomniac:1, villager:3`（共 9 = 6+3）   |
| 7    | `werewolf:2, seer:1, robber:1, troublemaker:1, insomniac:1, villager:4`（共 10 = 7+3）  |
| 8    | `werewolf:2, seer:1, robber:1, troublemaker:1, insomniac:1, villager:5`（共 11 = 8+3）  |
| 9    | `werewolf:2, seer:1, robber:1, troublemaker:1, insomniac:1, villager:6`（共 12 = 9+3）  |
| 10   | `werewolf:2, seer:1, robber:1, troublemaker:1, insomniac:1, villager:7`（共 13 = 10+3） |

房主在 waiting 房间可对**每种角色**的份数做增减（`0` 表示不下），自由混入 `minion`（爪牙）等；配置以这份映射存库并随 `board:<人数>` 缓存在本地。合法性只在 `start_game` 边界校验（Σ计数 == 人数+3）。

### 6.4 API 一览

| Verb | Path                 | Body                                              | 说明                                                                                                                                       |
| ---- | -------------------- | ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| GET  | `/api/csrf/`         | —                                                 | 取 CSRF token（唯一公开 GET，无凭据）                                                                                                      |
| POST | `/api/create_room/`  | `{roomid,userid,userpsw,avatar}`                  | 建房 + 创建房主                                                                                                                            |
| POST | `/api/join_room/`    | `{roomid,userid,userpsw,avatar}`                  | 加入/登录玩家                                                                                                                              |
| POST | `/api/set_board/`    | `{roomid,userid,userpsw,board:{role_code:count}}` | （房主）配置每种角色份数；waiting 阶段不校验；**响应回传 DB 上已保存的 `board`（与 `/api/room_state/`@waiting 同形状），供房主更新本地值** |
| POST | `/api/start_game/`   | `{roomid,userid,userpsw}`                         | （房主）发初始牌 + 设中央 + `phase=op`                                                                                                     |
| POST | `/api/night_action/` | `{roomid,userid,userpsw,choice}`                  | 阶段一提交操作（响应为 `phase=op` 的 `/api/room_state/` payload；`phase` 已非 `op` 时忽略此写）                                            |
| POST | `/api/room_state/`   | `{roomid,userid,userpsw}`                         | **唯一的轮询端点**：`phase` + 该 phase 的 payload（见下）                                                                                  |
| POST | `/api/reveal/`       | `{roomid,userid,userpsw}`                         | 阶段二**一次性**取结果（幂等；仅在 `phase=reveal` 时返回正文，不用于轮询）                                                                 |
| POST | `/api/vote/`         | `{roomid,userid,userpsw,target}`                  | （阶段二）投票处决对象（`""` 弃权）；按 DB 条件写，**当且仅当 `phase=reveal` 且本人未投**才落库                                            |
| POST | `/api/result/`       | `{roomid,userid,userpsw}`                         | 全员最终身份 + 被投出对象 + 胜负                                                                                                           |

**`/api/room_state/` 按 `phase` 返回不同 payload**（waiting/op/reveal/result 四态的前端唯一轮询与路由依据，详见 view-design.md §0.1）：

- `phase='waiting'` → `users, userCount, avatars, host, is_owner, board`
- `phase='op'` → `role, my_choice, submitted, submitted_count, total_count, deadline_ms`
- `phase='reveal'` → `voted`（**仅投票进度，不含揭晓内容**）
- `phase='result'` → 空（结果由 `/api/result/` 一次性给）

### 6.5 请求驱动的阶段推进

没有后台定时器。`room_state` 和 `night_action` 在请求中检查截止时间，只有到期才能推进 `op → reveal`；全员提前提交也必须等满。最后一票在同一事务内推进 `reveal → result`。阶段本身就是冻结操作和投票的条件，不另存结算布尔标记。

### 6.6 一致性与鲁棒性（丢包 / 离线 / 重放）

**核心不变式：DB 是唯一真值来源，每个阶段一写操作都以 `room.phase == 'op'` 为前置条件。** 由此自动得到全部鲁棒性：

- **统一响应格式**：`/api/night_action/`（提交）与 `phase='op'` 时的 `/api/room_state/`（轮询）返回**完全相同的结构**，服务端视为权威：

  ```json
  {
    "ok": true,
    "phase": "op",              // 驱动前端跳转：非 "op" 时就该去阶段二
    "role": "troublemaker",      // 我阶段一“正在操作的身份”界面
    "my_choice": { "target": "a", "target2": "b" },  // 我当前生效的操作，供阶段一 UI 回显
    "submitted": true,
    "submitted_count": 3, "total_count": 5,
    "deadline_ms": 7000
  }
  ```

  - 因为轮询和提交同格式，**提交丢了也没关系**：下一次轮询直接把我当前操作回显到 UI，我重交即可。
- **默认随机操作**：阶段一结束时，**从未提交**（离线/丢包/选择不做）的玩家，服务端在 `op→reveal` 切换时为ta**随机指定默认操作**，随正常操作一起结算。这是 best-effort，只保存补全后的原始操作，不另外存提交标记。
- **允许重报覆盖**：阶段一期间可多次提交，后者覆盖前者（best effort）。离线/反复改选都无妨。
- **DB 条件写保证原子**：每次阶段一写是 `UPDATE player SET choice=? WHERE id=? AND room.phase='op' AND 截止时间尚未到达`（或等价条件），**用受影响行数判定是否落库**。返回 0 行 = 房间已离开 `op`，此迟到/重复写**直接忽略**。一但房间切到 `reveal`，一切后续阶段一写都被拒绝——杜绝“先切到阶段二、后到的阶段一写篡改已锁定状态”。
- **1→2 切换一次性、原子**：在**单个事务**内：快照每个玩家最终操作（已提交或随机默认）→ 按序结算（强盗→捣蛋鬼→失眠者）→ 生成每个人的 reveal 记录 → 写死 `phase=reveal`。该事务提交前所有阶段一写可见；提交后一律被拒。
- **阶段二只回传一次**：客户端**只有在阶段一轮询报告 `phase=reveal` 后才进入阶段二**；进入时**一次性 `POST /api/reveal/` 拿到自己唯一的正文应答**（幂等，不轮询）。阶段二的轮询**不是**再要阶段一/揭晓结果，而是轮询**投票是否全员提交**，据此进入阶段三展示结果。
- **DB 聚合原子**：一个房间的全部状态（阶段、板子、各人操作、投票、中央牌、结算结果）都作为 `Room` 及相关表的**同一事务域**；任何对房间的变更都在单事务内完成，保证原子。SQLite 沿用阿瓦隆 “首条写语句先拿排他锁” 的套路避免竞态。
- **DB 是唯一真值来源，校验只在状态边界**：waiting 阶段板子允许“非法”——房主可能正在编辑、人数或角色还没配好（如总数≠人数+3），此时不强行报错。但**只有 `start_game` 把房间推进到阶段一（`phase=op`）时才必须校验**：`总牌数 == 人数 + 3`、各角色份数合法、且恰好覆盖“中央 3 张 + 每名玩家 1 张”；不合法则**拒绝开始并回滚，房间停留在 waiting**。进入阶段一后，一切以 **DB 里最终锁定的板子** 为准，前端任何临时设置（哪怕 localStorage 里缓存的那个）都不算数——**DB 才是一切的唯一真值来源**。同理，阶段一操作、投票的合法与否，也一律以 DB 中房间当时的 `phase` 判定。

---

## 7. 对局三视图（前端）

三个 View 共享一套轮询与跳转：`mounted` 时先 `POST /api/room_state/` 一次（凭据进 body，故为 POST，见 §0），再用 `setInterval(2s)` 轮询；`phase` 变化即 `$router.push` 到对应 View。玩家中途刷新页面也能靠这个重新进入正确阶段。

### 7.1 OperationView —— 阶段一（15 秒）

**页面职责：让每—个人都低着头在屏幕上“做操作”（人人必点），看到自己正在操作的身份、做出真实选择，但不显示任何结果，倒计时，收集选择。**

- **顶部**：倒计时圈（15→0）、已提交人数 N/总人数。
- **行动与掩护点选**：
  - 你的真实身份**有真实夜间行动**（独狼可选看中央牌 / 预言家 / 强盗 / 捣蛋鬼）→ 分配**该身份的操作界面**，你会看到自己就是这个身份，并做出**真实选择**：真捣蛋鬼在阶段一就看到“你是捣蛋鬼，请选两张”。
  - 无需选择（有狼同伴的狼人 / 爪牙 / 失眠者 / 村民）→ 服务端返回 `role=null`；前端明确提示无需操作，并提供本地点选按钮，不显示具体身份、不提交选择。
  - 服务端只收集真实行动；掩护点选不发送请求，不影响结算。
- **⚠️ 阶段一不显示任何“结果”**：你窥视到的牌、换到的牌、对方的身份，**在阶段一一律不展示**，只做选择；这些牌面/结果只在阶段二 `/reveal` 出现。
- **操作控件**：
  - 独狼/预言家：点中央 3 张牌中的 1 张 / 2 张（预言家选“看某人”或“看两张中央”）。
  - 强盗/捣蛋鬼：点选玩家牌 → 选中 → 确认。
  - 无需行动玩家：随意切换掩护选项，无需确认或提交。
- **交互**：选中高亮 → 确认提交 `POST /api/night_action/`；可改选直到提交。倒计时结束强制提交。
- 轮询 `/api/room_state/`（`phase='op'` payload 含 `deadline_ms` 与 `submitted_count/total_count`）拿倒计时与已提交人数；一旦 `phase` 变 `reveal` 就按 §0.1 统一逻辑跳 `/reveal`（真正的信息与身份展示）。

### 7.2 RevealView —— 阶段二（揭晓 + 投票）

**页面职责：进入阶段二即刻拉取一次真实的结算结果，并提供一个投票控件；可随时投、每人只投一次；阶段二轮询等待全员投完。**

- 进入时**一次性** `POST /api/reveal/` 拿到本玩家的**唯一正文应答**（幂等，之后不再重拉揭晓）。
- **你看到的信息**（按身份）：
  - 狼人/爪牙：显示狼队友名单（爪牙还提示“狼人不知道我是爪牙”）。
  - 独狼：显示你窥视的那张中央牌。
  - 预言家：显示你看到的玩家牌 / 两张中央牌。
  - 强盗：显示你换到的新身份（强盗交换完成当时看到的牌，之后仍可能被捣蛋鬼换走）。
  - 捣蛋鬼：提示“你交换了 A 与 B”（不显示牌）。
  - 失眠者：显示复核后的自己的牌。
- **投票控件**：列出所有玩家（含头像），选“处决对象”（可**弃权**）→ `POST /api/vote/ {target}`。**可随时投、且每人只投一次**（改投/重投被服务端拒绝）。
- **阶段二轮询**：`POST /api/room_state/`——轮询的**不是**阶段一/揭晓结果，而是**是否全员投完**；服务端聚合到全部投票、进入结果阶段时，轮询响应指示客户端跳 `/result`。
- （提示：此阶段发牌信息属于玩家私密，页面数据只含本玩家所见，不做全员广播。）

### 7.3 ResultView —— 阶段三（结果揭示）

**页面职责：全员投完后展示最终结果。**

- `POST /api/result/` 展示：
  - **被投出处决者** 的最终身份。
  - 所有人的最终身份卡（公开，因为已揭晓）。
  - 胜负横幅：村民胜 / 狼人胜（含爪牙修正逻辑，§1.2）。
  - 历史：本局关键事件时间线（谁换了谁、预言家看谁、票型），构型参考阿瓦隆 `renderVote`/history 卡片。
- **退出**：只提供返回主页（或“创建新房间”）。**不加“再来一局/回 WaitingRoom”**——一个房间只对应一局游戏，本局结束即终局；想再来请新开（或新进）一个房间。

---

## 8. 前端 `gameConfig.js`（显示层集中配置）

沿用阿瓦隆模式：后端只存**稳定角色 code**，前端统一显示与翻译。

- `ROLE_DISPLAY`：`werewolf/seer/robber/troublemaker/insomniac/villager/minion` → 名称（带 emoji）+ reveal 时的提示文案。
- `FACTION`：`werewolf`/`minion` → `evil`；其余 → `good`（强盗/失眠者/捣蛋鬼初始为村民，最终随交换后的牌）。
- `ERROR_MESSAGES`：与 endpoint-design.md §4 的错误 code 一一对应 → 中文：`roomid_taken` / `bad_request` / `room_not_found` / `wrong_password` / `bad_credentials` / `room_started` / `not_host` / `not_waiting` / `bad_players_count` / `bad_board` / `not_in_op` / `bad_choice` / `already_voted` / `bad_target` / `not_yet` / `not_in_reveal` / `not_done` …
- `boardTemplate(count)`、`boardDefaults`：供 waiting 房间展示与配置默认板子。
- `OPERATION_ROLES`：真实操作界面（`seer/robber/troublemaker` + 独狼）；无操作身份使用本地点选。

---

## 9. localStorage 键清单

| 键                     | 用途                               | 参考               |
| ---------------------- | ---------------------------------- | ------------------ |
| `roomId`               | 记住房间ID                         | 阿瓦隆             |
| `userId`               | 记住玩家ID                         | 阿瓦隆             |
| `userPsw`              | 记住玩家密码                       | 阿瓦隆             |
| `avatar`               | 当前玩家头像文件名                 | 阿瓦隆 `avatar.js` |
| `avatarFile:<name>`    | SVG 内容缓存                       | 阿瓦隆 `avatar.js` |
| `board:5` … `board:10` | 每个玩家人数对应的板子配置（房主） | 新增               |

---

## 10. 与阿瓦隆的差异汇总

1. 对局改为《一夜狼人》：角色、夜间结算、胜负条件不同；**爪牙独狼规则已按需求修正**。
2. **创建房间也带用户名/密码/头像，创建者即房主**。
3. waiting 房间新增**房主板子配置**，按人数缓存 `board:<n>`。
4. 对局拆成 3 个 View（操作 / 揭晓 / 投票+结果），由 `phase` 驱动。
5. 阶段一统一倒计时；无需行动者在前端随意点选，减少动作泄露。
6. 依赖管理用 **`uv`**（pyproject.toml + uv.lock）。
7. 实时性一律走 **HTTP 轮询**，不使用 websocket。
