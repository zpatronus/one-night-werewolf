<template>
  <div>
    <details class="container foldable">
      <summary>游戏规则<span class="when-open"> · 收起</span><span class="when-closed"> · 展开</span></summary>
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
            <div><dt>预言家</dt><dd>查看一名其他玩家的牌，或两张中央牌。看到的是换牌前的身份。</dd></div>
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
      <summary>流程说明<span class="when-open"> · 收起</span><span class="when-closed"> · 展开</span></summary>

      <ol class="phase-flow" aria-label="从身份分配到结算的完整流程">
        <li class="phase-panel">
          <h2><span class="step-number" aria-hidden="true">00</span>分配身份</h2>
          <p class="phase-description">服务器为每位玩家分配真实身份<br>此时身份保密，玩家尚不可见</p>
        </li>
        <li class="phase-panel action-phase">
          <h2><span class="step-number" aria-hidden="true">01</span>行动</h2>
          <p class="action-intro">系统根据你的真实身份，分配操作界面：</p>
          <div class="action-cases">
            <div class="action-card real-action">
              <h3>真实身份需要行动</h3>
              <p class="role-list">预言家 · 强盗<br>捣蛋鬼 · 独狼</p>
              <div class="action-result"><strong>操作真实身份</strong><span>你的选择会真正执行</span></div>
            </div>
            <div class="action-card decoy-action">
              <h3>真实身份无需行动</h3>
              <p class="role-list">村民 · 失眠者 · 爪牙<br>有狼同伴的狼人</p>
              <div class="action-result"><strong>操作随机假身份</strong><span>如村民看到强盗界面<br>选了人也不会真的换牌</span></div>
            </div>
          </div>
          <div class="shared-rule-box">
            <strong>人人都操作，谁也不知道界面上的身份是真是假。</strong>
            <p>照提示选择即可；真实身份与所有信息、结果，<br>都等到「揭晓与投票」才显示。</p>
          </div>
        </li>
        <li class="phase-panel">
          <h2><span class="step-number" aria-hidden="true">02</span>服务器结算行动</h2>
          <p class="phase-description">操作结束后，服务器忽略假身份的操作<br>按真实身份与正常夜间顺序计算结果，而非提交先后</p>
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
          <h2><span class="step-number" aria-hidden="true">03</span>揭晓与投票</h2>
          <p class="phase-description">此时才揭晓你的真实身份与操作结果<br>根据这些信息讨论，然后投票</p>
        </li>
        <li class="phase-panel">
          <h2><span class="step-number" aria-hidden="true">04</span>结算</h2>
          <p class="phase-description">公布所有人的身份与胜负</p>
        </li>
      </ol>
    </details>
    <details class="container foldable">
      <summary>常见问题<span class="when-open"> · 收起</span><span class="when-closed"> · 展开</span></summary>
      <dl class="faq-list">
        <div class="faq-item">
          <dt>为什么没有一般狼人杀那样的上帝喊人依次睁眼环节？</dt>
          <dd>因为可以把每个角色的夜拆成两部分：先操作，再看信息。比如强盗，第一步选一个人交换，第二步系统才告诉他换到什么牌；失眠者不用操作，第二步由系统告诉他自己的牌。所有角色第一步各自操作、互不影响，可以同时进行；但有些人的第二步依赖别人的第一步——比如失眠者看到的牌，就取决于强盗、捣蛋鬼之前有没有动过他的牌。所以系统让所有人先在第一步一起操作，再在第二步一起看到各自的信息。</dd>
        </div>
        <div class="faq-item">
          <dt>什么叫我在行动阶段看到的身份可能是假的？</dt>
          <dd>并发协议虽好，却带来一个场外信息问题：光看「谁在第一阶段玩手机」，就能猜出谁是夜里需要操作的角色。解决办法是——第一阶段即使你的身份不需要操作（比如你是村民），系统也不告诉你这一点，而是从需要操作的角色里随机发一个假身份给你，比如告诉你「你是强盗，选一张」。你此时分辨不出自己是真强盗，还是被分到假强盗的不操作角色。只有到了第二阶段、揭开初始真实身份时你才明白：如果是强盗，你刚才的选择会真的换牌；如果是村民，刚才的操作不会对游戏产生任何影响。</dd>
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
        <b>v1.1.0（2026-09-16）：</b>新增固定操作截止时间与倒计时；等待室邀请链接；揭晓页展示房间与玩家信息；后台房间管理；简洁优化身份描述。
      </p>
      <p>
        <b>v1.0.0（2026-09-14）：</b>首发版本。上线房间创建 / 加入、板子配置、夜间操作、揭晓与投票、结算全流程。
      </p>
    </div>
  </div>
</template>

<style scoped>
.foldable > summary { display: block; width: fit-content; max-width: 100%; margin: 0 auto; padding: 8px 18px; border-radius: 999px; border: 1px solid rgba(229, 189, 84, 0.4); background: rgba(229, 189, 84, 0.10); cursor: pointer; color: var(--accent); font-size: 0.9rem; font-weight: 700; line-height: 1.6; text-align: center; list-style: none; }
.foldable > summary::-webkit-details-marker { display: none; }
.foldable > summary:hover { background: rgba(229, 189, 84, 0.16); }
.foldable > summary span { color: inherit; font-size: 0.75rem; font-weight: 400; }
.foldable > summary:focus-visible { outline: 2px solid var(--accent); outline-offset: 4px; }
.foldable:not([open]) > summary .when-open, .foldable[open] > summary .when-closed { display: none; }
.rules-content { text-align: left; }
.rule-block { margin-top: 20px; padding-top: 18px; border-top: 1px solid var(--border); }
.rule-block h2 { margin-bottom: 10px; font-size: 0.95rem; }
.rule-block p { margin: 8px 0; font-size: 0.8rem; }
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
.faq-list dt { font-size: 0.82rem; font-weight: 700; line-height: 1.7; color: var(--accent); }
.faq-list dd { margin: 8px 0 0; font-size: 0.78rem; line-height: 1.8; color: var(--text-dim); }
.faq-list b { color: var(--text); }
.rules-content dd { margin: 4px 0 0; color: var(--text-dim); font-size: 0.78rem; line-height: 1.7; }
.win-rules > div { margin-top: 10px; padding: 12px; border: 1px solid var(--border); border-radius: 10px; background: var(--surface-2); }
p { line-height: 1.7; color: var(--text-dim); font-size: 0.9rem; }
.phase-flow { list-style: none; padding: 0; margin: 18px 0 0; }
.phase-panel { position: relative; padding: 14px 10px; border: 1px solid var(--border-strong); border-radius: 12px; background: var(--surface-2); }
.phase-panel + .phase-panel { margin-top: 34px; }
.phase-panel + .phase-panel::before { content: ""; position: absolute; left: 50%; top: -29px; height: 21px; border-left: 1px solid var(--accent); }
.phase-panel + .phase-panel::after { content: ""; position: absolute; left: calc(50% - 3px); top: -14px; width: 6px; height: 6px; border-right: 1px solid var(--accent); border-bottom: 1px solid var(--accent); transform: rotate(45deg); }
.step-number { display: grid; place-items: center; width: 28px; height: 28px; border: 1px solid var(--border-strong); border-radius: 50%; color: var(--accent); font-size: 0.72rem; font-weight: 700; }
h2 { display: flex; align-items: center; justify-content: center; gap: 8px; margin: 0 0 12px; font-size: 1rem; }
.action-phase { border-color: rgba(229, 189, 84, 0.3); background: rgba(229, 189, 84, 0.04); }
.phase-description { margin: 0; text-align: center; font-size: 0.78rem; }
.action-intro { margin: 0 0 12px; text-align: center; font-size: 0.78rem; }
.shared-rule-box { margin-top: 12px; padding: 12px 8px; border: 1px solid var(--border); border-radius: 8px; background: var(--surface-2); text-align: center; }
.shared-rule-box strong { font-size: 0.78rem; line-height: 1.7; color: var(--accent); }
.shared-rule-box p { margin: 6px 0 0; font-size: 0.75rem; }
.action-cases { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.action-card { padding: 12px 7px; border: 1px solid var(--border-strong); border-radius: 12px; text-align: center; background: var(--surface-2); }
.real-action { border-color: rgba(229, 189, 84, 0.35); background: rgba(229, 189, 84, 0.04); }
.decoy-action { border-style: dashed; }
h3 { margin: 6px 0; font-size: 0.8rem; }
.role-list { margin: 0 0 12px; font-size: 0.73rem; }
.action-result { border-top: 1px solid var(--border); padding-top: 10px; display: flex; flex-direction: column; gap: 5px; }
.action-result strong { color: var(--accent); font-size: 0.87rem; }
.decoy-action .action-result strong { color: var(--text); }
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
</style>
