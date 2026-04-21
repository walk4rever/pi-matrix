"use client";

import { useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "https://relay.air7.fun/pm/api";

function RegisterForm() {
  const searchParams = useSearchParams();
  const openId = searchParams.get("open_id") ?? "";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    const res = await fetch(`${API_URL}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password, open_id: openId }),
    });
    if (res.ok) {
      setSent(true);
    } else {
      const body = await res.json().catch(() => ({}));
      setError(body.detail ?? "注册失败，请重试。");
    }
    setLoading(false);
  }

  if (sent) {
    return (
      <div className="auth-page">
        <div className="auth-card" style={{ textAlign: "center" }}>
          <div className="status-icon">📬</div>
          <div className="status-title">查收邮件</div>
          <p className="status-desc">
            已发送绑定链接至<br />
            <strong style={{ color: "var(--claude-near-black)" }}>{email}</strong>
          </p>
          <div className="status-footer">
            点击邮件中的按钮，您的爱马仕员工自动上线。
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-card-header">
          <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", marginBottom: "0.4rem" }}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/logo.svg" alt="pi-matrix logo" width={36} height={36} />
            <div className="display-serif" style={{ fontSize: "1.6rem" }}>
              pi<span className="text-accent">-matrix</span>
            </div>
          </div>
          <p className="auth-card-subtitle">您的专属爱马仕员工，注册后即刻上线。</p>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <div>
              <label className="form-label">邮箱地址</label>
              <input
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="form-input"
              />
            </div>
            <div>
              <label className="form-label">密码</label>
              <input
                type="password"
                placeholder="至少 6 位"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={6}
                className="form-input"
              />
            </div>
            {error && <p className="form-error">{error}</p>}
            <button type="submit" disabled={loading} className="btn-primary">
              {loading ? "注册中..." : "注册"}
            </button>
          </div>
        </form>

        <p className="form-hint">
          注册后将收到绑定邮件，点击完成飞书绑定。
        </p>
      </div>
    </div>
  );
}

export default function RegisterPage() {
  return (
    <Suspense>
      <RegisterForm />
    </Suspense>
  );
}
