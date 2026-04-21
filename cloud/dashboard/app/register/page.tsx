"use client";

import { useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "https://relay.air7.fun/pm/api";

function RegisterForm() {
  const searchParams = useSearchParams();
  const openId = searchParams.get("open_id") ?? "";

  const [email, setEmail] = useState("");
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
      body: JSON.stringify({ email, open_id: openId }),
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
            点击邮件中的按钮，您的数字员工自动上线。
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-card-header">
          <div className="display-serif">
            pi<span className="text-accent">-matrix</span>
          </div>
          <p className="auth-card-subtitle">您的专属数字员工，输入邮箱即可开始。</p>
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
            {error && <p className="form-error">{error}</p>}
            <button type="submit" disabled={loading} className="btn-primary">
              {loading ? "发送中..." : "发送绑定链接"}
            </button>
          </div>
        </form>

        <p className="form-hint">
          点击链接即完成绑定，无需设置密码。
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
