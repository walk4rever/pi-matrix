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
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="bg-white p-8 rounded-xl shadow w-full max-w-sm text-center">
          <div className="text-4xl mb-4">📬</div>
          <h1 className="text-2xl font-bold mb-4">查收邮件</h1>
          <p className="text-gray-500 text-sm">
            已发送绑定链接至 <strong>{email}</strong>，点击邮件中的按钮即可完成绑定，您的数字员工自动上线。
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="bg-white p-8 rounded-xl shadow w-full max-w-sm">
        <h1 className="text-2xl font-bold mb-2 text-center">注册 pi-matrix</h1>
        <p className="text-gray-400 text-sm text-center mb-6">输入邮箱，我们发送绑定链接</p>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <input
            type="email"
            placeholder="您的邮箱"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="border rounded-lg px-4 py-2 outline-none focus:ring-2 focus:ring-black"
          />
          {error && <p className="text-red-500 text-sm">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="bg-black text-white rounded-lg py-2 font-semibold hover:bg-gray-800 disabled:opacity-50"
          >
            {loading ? "发送中..." : "发送绑定链接"}
          </button>
        </form>
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
