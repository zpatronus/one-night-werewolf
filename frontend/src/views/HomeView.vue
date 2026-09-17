<template>
  <div>
    <details class="container foldable">
      <summary><span class="fold-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M5 4h10a3 3 0 0 1 3 3v13H8a3 3 0 0 1-3-3V4Z"/><path d="M5 16h13M9 8h5M9 11h5"/></svg></span>游戏规则<span class="when-open"> · 收起</span><span class="when-closed"> · 展开</span></summary>
      <div class="rules-content">
        <section class="rule-block">
          <h2>游戏准备</h2>
          <p>3–10 人，只进行一夜行动和一轮投票。先选出「人数 + 3」张身份牌，公开本局有哪些身份及各自的张数，再洗匀随机分配。</p>
          <p>每人一张，剩下三张面朝下放在中央，称为「中央牌」。例如 5 人局用 8 张牌：5 张发给玩家，3 张留在中央。</p>
          <p>中央牌不属于任何人，可以被能力查验，但不行动、不投票，也不算场上的玩家。因此，牌组里有狼人，不代表一定有玩家是狼人。</p>
        </section>
        <section class="rule-block">
          <h2>角色与夜间能力</h2>
          <div class="faction-summary">
            <p><strong>好人阵营</strong>预言家、强盗、捣蛋鬼、失眠者、村民</p>
            <p><strong>坏人阵营</strong>狼人、爪牙</p>
          </div>
          <p class="rules-note">阵营由最终身份决定，换牌可能让玩家改变阵营。</p>
          <p>夜间能力按下列顺序生效：狼人、爪牙、预言家、强盗、捣蛋鬼、失眠者。村民没有夜间能力。</p>
          <dl class="role-rules">
            <div><dt>狼人</dt><dd>知道其他狼人玩家是谁。如果只有一名狼人玩家，他是「独狼」，可查看一张中央牌。</dd></div>
            <div><dt>爪牙</dt><dd>知道狼人玩家是谁；狼人不会因此知道谁是爪牙。</dd></div>
            <div><dt>预言家</dt><dd>查看一名其他玩家的<strong>初始身份（换牌前）</strong>，或查看两张中央牌的牌面。</dd></div>
            <div><dt>强盗</dt><dd>与一名其他玩家交换身份牌，并查看自己刚换到的牌。</dd></div>
            <div><dt>捣蛋鬼</dt><dd>在强盗之后，交换另外两名玩家的牌，不能换自己，也不能查看被换的牌。</dd></div>
            <div><dt>失眠者</dt><dd>在所有换牌结束后，查看自己的最终身份。</dd></div>
            <div><dt>村民</dt><dd>没有夜间能力，靠讨论与推理判断身份。</dd></div>
          </dl>
          <p class="rules-note">有查牌或换牌能力的角色必须选择目标，不能跳过。只有能力允许查看的牌和身份信息才可获知。</p>
        </section>
        <section class="rule-block">
          <h2>身份交换与阵营</h2>
          <div class="rule-principle">用最初身份的能力，按最终身份算输赢。</div>
          <p>夜间能力由最初分到的身份决定。身份牌被交换后，原有能力仍照常执行；获得新身份不会再发动新身份的能力。</p>
          <p>例如，强盗换到狼人牌后，不会再与狼人互认；若此后未再换牌，最终属于坏人阵营。捣蛋鬼即使先被强盗换走身份牌，仍要执行捣蛋鬼的交换。</p>
          <p>强盗获知的是交换当时拿到的身份，之后仍可能被捣蛋鬼换走。失眠者在所有交换结束后查看自己的牌；其他玩家不能额外查看最终身份，只能根据夜间信息与讨论进行推断。</p>
        </section>
        <section class="rule-block">
          <h2>讨论与投票</h2>
          <p>夜晚结束后，玩家根据各自的夜间信息展开讨论，推理每个人最终持有的身份。讨论中可以说真话、隐瞒或撒谎，但不能翻看或展示身份牌来证明自己的说法。</p>
          <p>每人投一名其他玩家或弃权，不能投自己，投出后不可更改。只投一轮，随后揭开所有身份并判断胜负。</p>
        </section>
        <section class="rule-block">
          <h2>胜负判定</h2>
          <p>以每位玩家<strong>最终持有的身份牌</strong>划分阵营：狼人、爪牙属于坏人阵营；预言家、强盗、捣蛋鬼、失眠者、村民属于好人阵营。</p>
          <p>同阵营的所有玩家共同获胜或落败，没有角色以个人存活为获胜条件。即使被处决，只要最终所属阵营获胜，该玩家仍然获胜。</p>
          <p>唯一最高票者被处决，即使只有一票。最高票平票则无人处决，但所有并列最高票者都参与下面的胜负判断。</p>
          <p class="rules-note">先检查所有玩家的最终身份，再看最高票玩家（含并列）中是否有目标身份。</p>
          <dl class="win-rules">
            <div><dt>所有玩家中，至少有一名狼人</dt><dd>最高票玩家中有狼人 → 好人阵营胜。<br>否则 → 坏人阵营胜。投出爪牙不能代替投出狼人。</dd></div>
            <div><dt>所有玩家中，没有狼人，但有爪牙</dt><dd>最高票玩家中有爪牙 → 好人阵营胜。<br>否则 → 坏人阵营胜。</dd></div>
            <div><dt>所有玩家中，既没有狼人，也没有爪牙</dt><dd>全员弃权 → 全员获胜。<br>只要有人投票 → 全员落败。</dd></div>
          </dl>
          <p class="rules-note">只计算玩家的最终身份，不计算中央牌。全员弃权时没有最高票者；若玩家中还有坏人，坏人阵营获胜。</p>
        </section>
      </div>
    </details>
    <details class="container guide foldable">
      <summary><span class="fold-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="3" width="6" height="6" rx="1.5"/><rect x="14" y="15" width="6" height="6" rx="1.5"/><path d="M7 9v9h7M12 6h5v6m-3-3 3 3 3-3"/></svg></span>流程说明<span class="when-open"> · 收起</span><span class="when-closed"> · 展开</span></summary>

      <ol class="phase-flow" aria-label="从身份分配到结算的完整流程">
        <li class="phase-panel">
          <h2><span class="step-number" aria-hidden="true">00</span>分配身份</h2>
          <p class="phase-description">服务器为每位玩家分配初始身份<br>每位玩家仅能查看自己的初始身份</p>
        </li>
        <li class="phase-panel action-phase">
          <h2><span class="step-number" aria-hidden="true">01</span>行动</h2>
          <p class="action-intro">所有玩家先查看自己的初始身份，再按提示操作：</p>
          <div class="action-cases">
            <div class="action-card real-action">
              <h3>需要行动</h3>
              <p class="role-list">预言家 · 强盗<br>捣蛋鬼 · 独狼</p>
              <div class="action-result"><strong>选择行动目标</strong><span>按角色能力执行</span></div>
            </div>
            <div class="action-card cover-action">
              <h3>无需行动</h3>
              <p class="role-list">村民 · 失眠者 · 爪牙<br>有狼同伴的狼人</p>
              <div class="action-result"><strong>随意点选屏幕</strong><span>界面明确提示无需行动<br>点选不会影响游戏结果</span></div>
            </div>
          </div>
          <div class="shared-rule-box">
            <strong>人人都看屏幕，避免从操作动作猜测身份。</strong>
            <p>需要行动时按身份选择；无需行动时随意点选。<br>夜间信息与行动结果，<br>在「查看夜间信息」时显示。</p>
          </div>
        </li>
        <li class="phase-panel">
          <h2><span class="step-number" aria-hidden="true">02</span>服务器结算行动</h2>
          <p class="phase-description">操作结束后，服务器结算夜间行动<br>按初始身份与夜间行动顺序计算结果，而非提交先后</p>
          <div class="resolution-example">
            <p class="example-label">结算顺序示例</p>
            <ol class="resolution-order" aria-label="预言家、强盗、捣蛋鬼、失眠者的结算顺序示例">
              <li>预言家</li>
              <li>强盗</li>
              <li>捣蛋鬼</li>
              <li>失眠者</li>
            </ol>
          </div>
        </li>
        <li class="phase-panel">
          <h2><span class="step-number" aria-hidden="true">03</span>查看夜间信息</h2>
          <p class="phase-description">所有玩家安静查看自己的夜间信息<br>请管理好表情，10 秒后自动进入讨论</p>
        </li>
        <li class="phase-panel">
          <h2><span class="step-number" aria-hidden="true">04</span>讨论与投票</h2>
          <p class="phase-description">根据夜间信息讨论，然后投票<br>中途加入此阶段可直接进入</p>
        </li>
        <li class="phase-panel">
          <h2><span class="step-number" aria-hidden="true">05</span>结算</h2>
          <p class="phase-description">公布所有人的身份与胜负</p>
        </li>
      </ol>
    </details>
    <details class="container foldable">
      <summary><span class="fold-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="8"/><path d="M9.5 9a2.5 2.5 0 0 1 5 .3c0 1.7-2.5 1.8-2.5 3.7M12 16h.01"/></svg></span>常见问题<span class="when-open"> · 收起</span><span class="when-closed"> · 展开</span></summary>
      <dl class="faq-list">
        <div class="faq-item">
          <dt>为什么没有一般狼人杀那样的上帝喊人依次睁眼环节？</dt>
          <dd>
            <p>如果把每个玩家看成一个进程，上帝依次喊人睁眼，就是让这些进程一个接一个地运行。不过，能不能并行，关键要看它们之间有没有数据依赖，而不是规则里有没有写先后顺序。</p>
            <p>拿强盗和捣蛋鬼来说：强盗要选一个人交换身份，捣蛋鬼要选另外两个人交换身份。两个人作出选择时，都不需要知道对方选了谁，所以这部分可以同时进行。但执行交换时，必须先处理强盗，再处理捣蛋鬼；失眠者则要等所有交换结束，才能查看自己的最终身份。也就是说，需要按顺序执行的是结算，不是玩家点屏幕的过程。</p>
            <p>因此，我们把夜晚拆成三步：同时收集选择，按规则结算，再分别显示信息。操作截止时间就是一个同步点：时间到了，服务器固定所有人的选择，为没提交的人补上默认操作，然后开始结算。谁的请求先到，不影响角色的行动顺序。显示结果时也要区分读取的是哪个时刻的状态：预言家看初始身份，强盗看自己刚交换到的身份，失眠者看最终身份。</p>
            <p>这和并行程序的思路一样：没有依赖的部分同时做，有依赖的部分保留顺序。这样既能遵守夜间规则，也不用让所有人轮流等着操作手机。</p>
          </dd>
        </div>
        <div class="faq-item">
          <dt>为什么无需行动也要点选屏幕？</dt>
          <dd>如果只有需要行动的玩家操作手机，其他人可能从动作猜测身份。因此，村民、失眠者、爪牙和有狼同伴的狼人会看到「你的身份夜间无需操作」的提示，并可随意点选屏幕上的选项。点选不会影响游戏结果，也无需提交。所有玩家都等待同一个倒计时结束，再查看夜间信息与行动结果。</dd>
        </div>
      </dl>
    </details>
    <div class="container">
      <div class="subtitle">源代码、许可证与友链</div>
      <p>
        源代码：
        <a href="https://github.com/zpatronus/one-night-werewolf" target="_blank" rel="noopener">github.com/zpatronus/one-night-werewolf</a>
      </p>
      <p>
        许可证：<a href="https://github.com/zpatronus/one-night-werewolf/blob/main/LICENSE" target="_blank" rel="noopener">AGPL-3.0</a>
      </p>
      <p>
        线上阿瓦隆：<a href="https://goa.zijuny.dev/" target="_blank" rel="noopener">goa.zijuny.dev</a>
      </p>
    </div>
    <div class="container">
      <div class="subtitle">更新日志</div>
      <p>
        <b>v1.2.0（2026-09-17）：</b>新增「再来一局」与自动加入；建房沿用本地板子；优化房间号生成；夜间统一显示初始身份，移除假身份并提供掩护点选；新增 10 秒夜间信息查看页；完善规则与常见问题，新增源码与许可证入口；更新月夜背景与页面样式。
      </p>
      <p>
        <b>v1.1.0（2026-09-16）：</b>新增固定操作截止时间与倒计时；等待室邀请链接；揭晓页展示房间与玩家信息；后台房间管理；简洁优化身份描述。
      </p>
      <p>
        <b>v1.0.0（2026-09-14）：</b>首发版本。上线房间创建 / 加入、板子配置、夜间操作、揭晓与投票、结算全流程。
      </p>
    </div>
  </div>
</template>

<style scoped>
.foldable > summary { display: flex; align-items: center; width: 100%; margin: 0; padding: 4px 0; cursor: pointer; color: var(--text); font-size: 1.05rem; font-weight: 650; line-height: 1.6; text-align: left; list-style: none; }
.foldable > summary::-webkit-details-marker { display: none; }
.foldable > summary:hover { color: var(--accent-hover); }
.foldable > summary .when-open, .foldable > summary .when-closed { margin-left: auto; color: var(--text-dim); font-size: 0.72rem; font-weight: 400; }
.foldable > summary:focus-visible { outline: 2px solid var(--accent); outline-offset: 4px; }
.foldable:not([open]) > summary .when-open, .foldable[open] > summary .when-closed { display: none; }
.rules-content { text-align: left; }
.rule-block { margin-top: 20px; padding-top: 18px; border-top: 1px solid var(--border); }
.rule-block h2 { margin-bottom: 10px; font-size: 0.95rem; }
.rule-block p { margin: 10px 0; font-size: 0.82rem; line-height: 1.9; }
.rule-block .rules-note { font-size: 0.75rem; }
.faction-summary { padding: 10px 12px; border: 1px solid var(--border); border-radius: 10px; background: var(--surface-2); }
.faction-summary strong { display: block; margin-bottom: 3px; }
.rule-principle { padding: 12px 8px; border: 1px solid rgba(229, 189, 84, 0.3); border-radius: 10px; background: rgba(229, 189, 84, 0.06); text-align: center; color: var(--accent); font-size: 0.85rem; font-weight: 700; line-height: 1.7; }
.team-label { margin: 16px 0 8px; color: var(--accent); font-size: 0.75rem; font-weight: 700; }
.role-rules, .win-rules { margin: 0; }
.role-rules > div { display: grid; grid-template-columns: 3.5em minmax(0, 1fr); gap: 10px; padding: 9px 0; border-bottom: 1px solid var(--border); }
.role-rules > div:last-child { border-bottom: 0; }
.rules-content .role-rules dd { margin: 0; }
.rules-content dt { font-size: 0.8rem; font-weight: 600; line-height: 1.7; }
.faq-list { margin: 0; text-align: left; }
.faq-list > div { padding: 12px 2px; }
.faq-list > div + div { border-top: 1px solid var(--border); }
.faq-list dt { font-size: 0.88rem; font-weight: 700; line-height: 1.7; color: var(--accent); }
.faq-list dd { margin: 8px 0 0; font-size: 0.82rem; line-height: 1.95; color: var(--text-dim); }
.faq-list dd p { margin: 10px 0 0; font-size: inherit; line-height: inherit; }
.faq-list dd p:first-child { margin-top: 0; }
.faq-list b { color: var(--text); }
.rules-content dd { margin: 4px 0 0; color: var(--text-dim); font-size: 0.78rem; line-height: 1.7; }
.win-rules > div { margin-top: 10px; padding: 12px; border: 1px solid var(--border); border-radius: 10px; background: var(--surface-2); }
p { line-height: 1.7; color: var(--text-dim); font-size: 0.9rem; }
.phase-flow { list-style: none; padding: 0; margin: 18px 0 0; }
.phase-panel { position: relative; padding: 16px; border: 1px solid var(--border); border-radius: 12px; background: var(--surface-2); }
.phase-panel + .phase-panel { margin-top: 20px; }
.phase-panel + .phase-panel::before { content: ""; position: absolute; left: 30px; top: -21px; height: 20px; border-left: 1px solid var(--accent); }

.step-number { display: grid; place-items: center; width: 28px; height: 28px; border: 1px solid rgba(229, 189, 84, 0.25); border-radius: 8px; background: rgba(229, 189, 84, 0.06); color: var(--accent); font-size: 0.72rem; font-weight: 700; }
h2 { display: flex; align-items: center; justify-content: flex-start; gap: 10px; margin: 0 0 12px; font-size: 1rem; }
.action-phase { border-color: rgba(229, 189, 84, 0.3); background: rgba(229, 189, 84, 0.04); }
.phase-description { margin: 0; text-align: left; font-size: 0.8rem; line-height: 1.85; }
.action-intro { margin: 0 0 14px; text-align: left; font-size: 0.8rem; }
.shared-rule-box { margin-top: 12px; padding: 12px 8px; border: 1px solid var(--border); border-radius: 8px; background: var(--surface-2); text-align: center; }
.shared-rule-box strong { font-size: 0.78rem; line-height: 1.7; color: var(--accent); }
.shared-rule-box p { margin: 6px 0 0; font-size: 0.75rem; }
.action-cases { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.action-card { padding: 12px 7px; border: 1px solid var(--border-strong); border-radius: 12px; text-align: center; background: var(--surface-2); }
.real-action { border-color: rgba(229, 189, 84, 0.35); background: rgba(229, 189, 84, 0.04); }
.cover-action { border-style: dashed; }
h3 { margin: 6px 0; font-size: 0.8rem; }
.role-list { margin: 0 0 12px; font-size: 0.73rem; }
.action-result { border-top: 1px solid var(--border); padding-top: 10px; display: flex; flex-direction: column; gap: 5px; }
.action-result strong { color: var(--accent); font-size: 0.87rem; }
.cover-action .action-result strong { color: var(--text); }
.action-result span { font-size: 0.7rem; line-height: 1.7; color: var(--text-dim); }
.resolution-example { margin-top: 14px; padding-top: 12px; border-top: 1px solid var(--border); }
.example-label { margin: 0 0 10px; text-align: center; color: var(--text-dim); font-size: 0.73rem; }
.resolution-order { display: flex; align-items: center; justify-content: center; list-style: none; margin: 0; padding: 0; }
.resolution-order li { display: flex; align-items: center; color: var(--text); font-size: 0.78rem; font-weight: 600; white-space: nowrap; }
.resolution-order li + li::before { content: "→"; margin: 0 9px; color: var(--accent); font-weight: 400; }
@media (max-width: 360px) {
  .resolution-order li + li::before { margin: 0 6px; }
  .guide { padding: 16px 10px; }
  .action-cases { gap: 6px; }
}
.container { padding: 22px; }
.container.foldable {
  padding: 0;
  margin: 10px auto;
  border-color: rgba(229, 189, 84, 0.16);
  border-radius: 14px;
  overflow: hidden;
}
.foldable::before { display: none; }
.foldable > summary {
  min-height: 70px;
  padding: 14px 18px;
  gap: 12px;
  font-size: 0.95rem;
  background: linear-gradient(110deg, rgba(229, 189, 84, 0.045), transparent 65%);
}
.foldable > summary:hover { background: rgba(229, 189, 84, 0.07); }
.foldable > summary:focus-visible { outline-offset: -3px; border-radius: 12px; }
.fold-icon { display: grid; place-items: center; width: 36px; height: 36px; flex-shrink: 0; border: 1px solid rgba(229, 189, 84, 0.18); border-radius: 10px; background: rgba(229, 189, 84, 0.06); color: var(--accent); }
.fold-icon svg { width: 21px; height: 21px; color: inherit; }
.foldable > summary::after { content: ''; width: 6px; height: 6px; flex-shrink: 0; margin-left: 2px; border-right: 1.5px solid var(--accent); border-bottom: 1.5px solid var(--accent); transform: rotate(45deg) translateY(-2px); }
.foldable[open] > summary::after { transform: rotate(225deg) translate(-1px, -1px); }
.foldable > .rules-content, .foldable > .faq-list { padding: 0 20px 20px; }
.foldable > .phase-flow { margin: 0; padding: 20px; }

.foldable[open] > summary { border-bottom: 1px solid var(--border); }
.rule-block:first-child { margin-top: 18px; padding-top: 0; border-top: 0; }
.rule-block h2 { font-size: 0.95rem; color: var(--accent-hover); }
.role-rules > div { padding: 12px 0; gap: 14px; }
.role-rules dt { color: var(--text); }
.faction-summary { display: grid; gap: 12px; padding: 14px; }
.faction-summary p { margin: 0; }
.faction-summary strong { font-size: 0.75rem; color: var(--accent); }
.win-rules > div { padding: 14px; border-left: 2px solid rgba(229, 189, 84, 0.55); }
.rules-content dd { line-height: 1.85; }
.faq-list > div { padding: 18px 0; }
.faq-list > div:last-child { padding-bottom: 0; }
.container > .subtitle { margin: 0 0 18px; text-align: left; font-size: 1.05rem; font-weight: 650; letter-spacing: 0; color: var(--text); }
.container > p { margin: 0; padding: 14px 0; font-size: 0.8rem; line-height: 1.9; overflow-wrap: anywhere; }
.container > p + p { border-top: 1px solid var(--border); }
.container > p:last-child { padding-bottom: 0; }
.container > p b { display: block; color: var(--accent-hover); font-size: 0.82rem; margin-bottom: 7px; }
a { text-underline-offset: 4px; text-decoration-color: rgba(229, 189, 84, 0.4); }
a:hover { color: var(--accent-hover); text-decoration-color: currentColor; }
@media (max-width: 360px) {
  .container { padding: 18px 14px; }
  .phase-panel { padding: 14px 10px; }
  .action-card { padding: 10px 5px; }
  .resolution-order { flex-wrap: wrap; row-gap: 6px; }
}
</style>
