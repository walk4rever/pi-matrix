export default function PricingSection() {
  return (
    <section className="pricing-section" id="pricing">
      <div className="container">
        <p className="section-overline">选择您的方案</p>
        <h2 className="section-title">您的 AI 员工，从今天开始积累。</h2>
        <p className="pricing-subtitle">
          先在云端体验"被 AI 记住"的感觉——30 天后您积累的记忆，可以一键迁移到专属 Mac mini。
        </p>

        <div className="pricing-grid">
          {/* Cloud trial */}
          <div className="pricing-card">
            <div className="pricing-badge-wrap">
              <span className="pricing-badge neutral">体验入口</span>
            </div>
            <div className="pricing-tier">云端版</div>
            <div className="pricing-price">
              <span className="pricing-amount">免费</span>
              <span className="pricing-period">前 30 天</span>
            </div>
            <p className="pricing-desc">无需硬件，扫码即用。体验真正"越用越懂你"的 AI 员工。试用期积累的记忆，购买 Mac mini 后无缝迁移。</p>
            <ul className="pricing-features">
              <li>功能与 Mac mini 版完全一致</li>
              <li>结构化记忆积累（记忆可迁移）</li>
              <li>飞书对话，即时响应</li>
              <li>Dashboard 控制台</li>
              <li className="pricing-feature-dim">30 天后 ¥199/月 或升级 Mac mini</li>
            </ul>
            <a href="#how-it-works" className="btn-pricing-secondary">扫码开始体验</a>
          </div>

          {/* Mac mini — hero */}
          <div className="pricing-card pricing-card-featured">
            <div className="pricing-badge-wrap">
              <span className="pricing-badge accent">主力产品</span>
            </div>
            <div className="pricing-tier">Mac mini 版</div>
            <div className="pricing-price">
              <span className="pricing-amount">¥4,800</span>
              <span className="pricing-period">设备一次性费用</span>
            </div>
            <div className="pricing-plus">
              <span className="pricing-plus-label">+</span>
              <span className="pricing-plus-value">¥149 – 299</span>
              <span className="pricing-plus-unit">/月 云服务</span>
            </div>
            <p className="pricing-desc">预配置 Mac mini 送货上门。开箱连 WiFi，飞书发消息，您的 AI 员工立即就绪。数据永远属于您。</p>
            <ul className="pricing-features">
              <li>物理级隐私：数据锁在您桌上</li>
              <li>断网可用，一 U 盘带走一切</li>
              <li>结构化记忆永久积累，不设上限</li>
              <li>LLM 网关 + 记忆服务 + 增量备份</li>
              <li>OTA 自动更新，零运维</li>
              <li>试用期记忆一键迁移</li>
            </ul>
            <a href="mailto:2451269@qq.com?subject=Mac mini 版咨询" className="btn-pricing-primary">立即咨询购买</a>
            <p className="pricing-note">早鸟价 ¥3,999 + ¥99/月（锁定一年），名额有限</p>
          </div>

          {/* Enterprise teaser */}
          <div className="pricing-card">
            <div className="pricing-badge-wrap">
              <span className="pricing-badge neutral">即将开放</span>
            </div>
            <div className="pricing-tier">企业版</div>
            <div className="pricing-price">
              <span className="pricing-amount">¥599</span>
              <span className="pricing-period">/人/月</span>
            </div>
            <p className="pricing-desc">让整个团队都拥有专属 AI 员工。AI 数据不出公司，团队知识永久沉淀。</p>
            <ul className="pricing-features">
              <li>Mac mini 企业版硬件方案</li>
              <li>SSO 企业单点登录</li>
              <li>团队管理与权限控制</li>
              <li>审计日志与合规支持</li>
              <li>多员工协同编排</li>
            </ul>
            <a href="mailto:2451269@qq.com?subject=企业版咨询" className="btn-pricing-secondary">联系我们</a>
          </div>
        </div>

        {/* Service breakdown */}
        <div className="pricing-service-wrap">
          <p className="section-overline" style={{ marginBottom: "1.5rem" }}>云服务包含内容</p>
          <div className="pricing-service-grid">
            <div className="pricing-service-item">
              <div className="pricing-service-icon">🧠</div>
              <div>
                <div className="pricing-service-title">记忆服务</div>
                <div className="pricing-service-desc">结构化记忆存储与语义检索。AI 越用越懂您，跨设备记忆实时同步。</div>
              </div>
            </div>
            <div className="pricing-service-item">
              <div className="pricing-service-icon">⚡</div>
              <div>
                <div className="pricing-service-title">LLM 网关</div>
                <div className="pricing-service-desc">无需管理 API Key，自动选择最优模型（Haiku/Sonnet），按配额使用。</div>
              </div>
            </div>
            <div className="pricing-service-item">
              <div className="pricing-service-icon">☁️</div>
              <div>
                <div className="pricing-service-title">增量备份</div>
                <div className="pricing-service-desc">设备数据自动备份到加密云存储，更换设备时一键完整恢复。</div>
              </div>
            </div>
            <div className="pricing-service-item">
              <div className="pricing-service-icon">🔄</div>
              <div>
                <div className="pricing-service-title">OTA 自动更新</div>
                <div className="pricing-service-desc">AI 能力持续升级，无需任何操作，始终运行最新版本。</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
