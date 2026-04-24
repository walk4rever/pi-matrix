"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { supabase } from "@/lib/supabase";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      if (data.session) router.replace("/dashboard");
    });
  }, [router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    const { error: signInError } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    if (signInError) {
      setError(signInError.message || "邮箱或密码错误，请重试。");
      setLoading(false);
      return;
    }

    router.replace("/dashboard");
    setLoading(false);
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
          <p className="auth-card-subtitle">输入邮箱与密码登录控制台。</p>
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
                placeholder="请输入密码"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="form-input"
              />
            </div>
            {error && <p className="form-error">{error}</p>}
            <button type="submit" disabled={loading} className="btn-primary">
              {loading ? "登录中..." : "登录"}
            </button>
            <p className="form-hint" style={{ marginTop: "0.5rem" }}>
              若没有账号，请先在飞书扫码进入 iHermes 完成注册。
            </p>
            <p className="form-hint" style={{ marginTop: "0.2rem" }}>
              <Link href="/" className="workspace-action-link" style={{ fontSize: "0.78rem" }}>
                返回首页查看注册流程
              </Link>
            </p>
          </div>
        </form>
      </div>
    </div>
  );
}
