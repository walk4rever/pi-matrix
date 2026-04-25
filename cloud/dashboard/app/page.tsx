import Link from "next/link";
import FeishuQRCode from "@/components/FeishuQRCode";

export default function HomePage() {
  return (
    <>
      {/* Nav */}
      <nav className="navbar">
        <div className="container nav-inner">
          <Link href="/" className="brand">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/logo.svg" alt="pi-matrix" width={28} height={28} />
            <span className="brand-name">pi<span>-matrix</span></span>
          </Link>
          <Link href="/console" className="nav-console-link">
            控制台
          </Link>
        </div>
      </nav>

      <main>
        {/* Hero */}
        <section className="hero">
          <div className="container">
            <p className="hero-overline">Private AI Digital Employee · Owned by You</p>
            <h1 className="hero-headline">
              您的 AI 员工，<br />永远属于您。
            </h1>
            <p className="hero-subline" style={{ marginTop: "1.5rem", fontSize: "1.25rem", opacity: 0.8, maxWidth: "600px", marginInline: "auto" }}>
              不仅是工具，更是资产。它住在您桌上的盒子里，记住您的一切，且只为您服务。
            </p>
          </div>
        </section>

        {/* How it works */}
        <section className="steps-section" id="how-it-works">
          <div className="container">
            <p className="section-overline">三步完成注册</p>
            <h2 className="section-title">扫码 → 发消息 → 注册绑定</h2>
            <div className="steps-grid">
              <div className="step-card">
                <div className="step-number">01</div>
                <div className="step-title">手机飞书扫码进入 iHermes</div>
                <p className="step-desc">
                  打开手机端飞书，扫描下方二维码，进入 iHermes 对话窗口。
                </p>
                <FeishuQRCode />
              </div>
              <div className="step-card">
                <div className="step-number">02</div>
                <div className="step-title">发送消息，获取注册卡</div>
                <p className="step-desc">
                  给 iHermes 发送任意消息，系统会自动回复您的专属注册卡片。
                </p>
              </div>
              <div className="step-card">
                <div className="step-number">03</div>
                <div className="step-title">完成注册并邮箱绑定</div>
                <p className="step-desc">
                  点击注册卡完成注册，再到邮箱点击确认链接完成绑定。
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Features */}
        <section className="features-section">
          <div className="container">
            <p className="section-overline">核心价值</p>
            <h2 className="section-title">不只是对话，而是资产。</h2>
            <div className="features-grid">
              <div className="feature-card">
                <div className="feature-icon">🧠</div>
                <div className="feature-title">资产化记忆</div>
                <p className="feature-desc">
                  大多数 AI 阅后即焚，我们则通过结构化记忆为您建立专属图谱。
                  用得越久，它越懂您的偏好、项目与风格，成为您不可或缺的数字资产。
                </p>
              </div>
              <div className="feature-card">
                <div className="feature-icon">🔒</div>
                <div className="feature-title">物理级安全</div>
                <p className="feature-desc">
                  您可以选择将 AI 运行在专属 Mac mini 硬件中。
                  核心数据物理锁定在本地，不流向云端，不被用于模型训练，隐私即正义。
                </p>
              </div>
              <div className="feature-card">
                <div className="feature-icon">⚡</div>
                <div className="feature-title">工业级稳定性</div>
                <p className="feature-desc">
                  内置经过严格验证的工业级技能包（Verified Skills）。
                  拒绝幻觉，在飞书文档自动化、数据分析等复杂任务中提供稳定结果。
                </p>
              </div>
              <div className="feature-card">
                <div className="feature-icon">📱</div>
                <div className="feature-title">端云协同</div>
                <p className="feature-desc">
                  如同 iPhone 配合 iCloud。
                  本地硬件保障安全与所有权，云端服务提供最前沿的算力网关与加密备份。
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Dark CTA */}
        <section className="dark-cta">
          <div className="container">
            <h2 className="dark-cta-title">开始构建您的专属 AI 资产。</h2>
            <p className="dark-cta-sub">从飞书开始，体验一个真正属于您的 AI 员工。</p>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="footer">
        <div className="container">
          <p className="footer-copy" style={{ textAlign: "center" }}>
            © {new Date().getFullYear()} pi-matrix · Powered by Air7.fun
          </p>
        </div>
      </footer>
    </>
  );
}
