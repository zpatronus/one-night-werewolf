<template>
  <div>
    <section class="container guide" aria-labelledby="guide-title">
      <h1 id="guide-title" class="subtitle">流程说明</h1>

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
    </section>
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
