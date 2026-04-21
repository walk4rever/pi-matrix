import Link from "next/link";

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
          <Link href="/register" className="btn-nav">立即注册</Link>
        </div>
      </nav>

      <main>
        {/* Hero */}
        <section className="hero">
          <div className="container">
            <p className="hero-overline">AI Digital Employee · Powered by Air7.fun</p>
            <h1 className="hero-headline">
              您的数字员工，<br />在飞书候命。
            </h1>
            <p className="hero-sub">
              pi-matrix 为每位用户分配专属 AI 容器，直接在飞书对话，
              无需任何配置，注册即上线。
            </p>
            <div className="hero-cta">
              <Link href="/register" className="btn-hero">免费注册 →</Link>
              <a href="#how-it-works" className="btn-ghost">了解流程</a>
            </div>
          </div>
        </section>

        {/* How it works */}
        <section className="steps-section" id="how-it-works">
          <div className="container">
            <p className="section-overline">三步上线</p>
            <h2 className="section-title">从注册到对话，三步完成。</h2>
            <div className="steps-grid">
              <div className="step-card">
                <div className="step-number">01</div>
                <div className="step-title">注册账号</div>
                <p className="step-desc">
                  填写邮箱和密码，系统立即发送绑定邮件并为您预热专属 AI 容器。
                </p>
              </div>
              <div className="step-card">
                <div className="step-number">02</div>
                <div className="step-title">绑定飞书</div>
                <p className="step-desc">
                  点击邮件中的链接，浏览器自动完成飞书账号绑定，无需手动操作。
                </p>
              </div>
              <div className="step-card">
                <div className="step-number">03</div>
                <div className="step-title">开始对话</div>
                <p className="step-desc">
                  回到飞书直接发消息，您的数字员工即刻响应，随时待命。
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
            <h2 className="dark-cta-title">现在就给自己配一位<br />不下班的数字员工。</h2>
            <p className="dark-cta-sub">免费注册，三分钟内上线。</p>
            <Link href="/register" className="btn-hero">免费注册 →</Link>
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
