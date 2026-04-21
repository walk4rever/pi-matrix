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
      <main className="min-h-screen bg-parchment flex items-center justify-center px-4">
        <div
          className="bg-ivory border border-border-cream rounded-2xl shadow-whisper w-full max-w-sm p-10 text-center"
        >
          <div className="text-5xl mb-6">📬</div>
          <h1 className="font-serif text-2xl font-medium text-nearblack mb-3" style={{ lineHeight: 1.2 }}>
            查收邮件
          </h1>
          <p className="text-olive-gray text-sm leading-relaxed">
            已发送绑定链接至<br />
            <span className="text-nearblack font-medium">{email}</span>
          </p>
          <p className="text-stone-gray text-xs mt-4 leading-relaxed">
            点击邮件中的按钮，您的数字员工自动上线。
          </p>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-parchment flex items-center justify-center px-4">
      <div className="bg-ivory border border-border-cream rounded-2xl shadow-whisper w-full max-w-sm p-10">
        <div className="mb-8">
          <h1
            className="font-serif text-3xl font-medium text-nearblack mb-2"
            style={{ lineHeight: 1.2 }}
          >
            pi-matrix
          </h1>
          <p className="text-olive-gray text-sm leading-relaxed">
            您的专属数字员工，输入邮箱即可开始。
          </p>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label className="block text-xs font-medium text-stone-gray mb-1.5 tracking-wide uppercase">
              邮箱地址
            </label>
            <input
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full bg-parchment border border-border-warm rounded-xl px-4 py-2.5 text-nearblack text-sm placeholder-stone-gray outline-none transition focus:border-[#3898ec] focus:ring-2 focus:ring-[#3898ec]/20"
            />
          </div>

          {error && (
            <p className="text-[#b53333] text-xs leading-relaxed">{error}</p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-terracotta text-ivory rounded-xl py-2.5 text-sm font-medium transition hover:bg-coral disabled:opacity-50 disabled:cursor-not-allowed"
            style={{ boxShadow: "0px 0px 0px 1px #c96442" }}
          >
            {loading ? "发送中..." : "发送绑定链接"}
          </button>
        </form>

        <p className="text-stone-gray text-xs text-center mt-6 leading-relaxed">
          链接发送至邮箱，点击即完成绑定，无需设置密码。
        </p>
      </div>
    </main>
  );
}

export default function RegisterPage() {
  return (
    <Suspense>
      <RegisterForm />
    </Suspense>
  );
}
