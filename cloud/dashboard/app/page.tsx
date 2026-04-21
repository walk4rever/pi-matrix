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
        </div>
      </nav>

      <main>
        {/* Hero */}
        <section className="hero">
          <div className="container">
            <p className="hero-overline">AI Digital Employee · Powered by Air7.fun</p>
            <h1 className="hero-headline">
              您的爱马仕员工，<br />在飞书候命。
            </h1>
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
            <p className="section-overline">核心能力</p>
            <h2 className="section-title">不只是聊天机器人。</h2>
            <div className="features-grid">
              <div className="feature-card">
                <div className="feature-icon">🧠</div>
                <div className="feature-title">专属 AI 实例</div>
                <p className="feature-desc">
                  每位用户独享一个 Hermes AI 容器，数据完全隔离，
                  记忆与上下文持续积累，越用越懂你。
                </p>
              </div>
              <div className="feature-card">
                <div className="feature-icon">💬</div>
                <div className="feature-title">飞书原生体验</div>
                <p className="feature-desc">
                  在您最熟悉的工作平台直接对话，无需切换 App，
                  消息收到立刻回复，支持 Markdown 渲染。
                </p>
              </div>
              <div className="feature-card">
                <div className="feature-icon">⚡</div>
                <div className="feature-title">工具调用能力</div>
                <p className="feature-desc">
                  内置代码执行、文件读写、终端操作、网络搜索等 16 种工具，
                  真正完成任务，而不只是给建议。
                </p>
              </div>
              <div className="feature-card">
                <div className="feature-icon">🔒</div>
                <div className="feature-title">私有部署架构</div>
                <p className="feature-desc">
                  容器运行在您信任的云上，LLM 调用通过私有 Gateway，
                  对话内容不流向任何第三方平台。
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Dark CTA */}
        <section className="dark-cta">
          <div className="container">
            <h2 className="dark-cta-title">先在飞书发一条消息，<br />让爱马仕员工开始工作。</h2>
            <p className="dark-cta-sub">从飞书触发注册流程，几分钟内即可上线。</p>
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
