<script setup>
import { ROLE_DISPLAY, OPERATION_ROLES } from '../gameConfig'
</script>

<template>
  <div>
    <div class="container">
      <div class="subtitle">-- 玩法说明 --</div>
      <p class="notice">
        一夜狼人：每局只需几分钟。所有人低头操作一次 → 统一揭晓 → 投出一个人 → 揭晓胜负。
      </p>
      <p>
        <b>创建房间：</b>
        前往“创建房间”选项卡，选择房间ID，并设置你的玩家ID与密码。
      </p>
      <p>
        <b>创建玩家 / 加入房间：</b>
        房间已创建后，前往“加入房间”选项卡，输入房间ID与你的玩家ID、密码即可加入；若该玩家ID尚未存在，则会初始化一个新玩家。
      </p>
      <p>
        <b>胜负判定：</b>
        好人阵营想把狼人（或全场无狼时的独爪牙）投出去；无人被投或平票时，狼人阵营获胜。
      </p>
    </div>

    <div class="container">
      <div class="subtitle">-- 角色一览 --</div>
      <div class="board">
        <span v-for="(r, code) in ROLE_DISPLAY" :key="code" class="role-chip" :class="r.faction">
          {{ r.emoji }} {{ r.name }}
          <template v-if="OPERATION_ROLES.includes(code)">（行动）</template>
        </span>
      </div>
      <p class="subsubtitle" style="text-align:center">
        狼人阵营：狼人、爪牙 · 好人阵营：预言家、强盗、捣蛋鬼、失眠者、村民
      </p>
    </div>
  </div>
</template>

<style scoped>
p { line-height: 1.8; color: var(--text-dim); font-size: 0.95rem; }
.role-chip {
  display: inline-block;
  margin: 3px 6px;
  padding: 5px 12px;
  border-radius: 999px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  font-size: 0.95rem;
}
.role-chip.evil { border-color: rgba(255, 139, 69, 0.4); }
.role-chip.good { border-color: rgba(69, 183, 245, 0.4); }
</style>