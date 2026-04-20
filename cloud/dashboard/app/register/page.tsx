"use client";

import { useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { supabase } from "@/lib/supabase";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://matrix.air7.fun";

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

    const redirectTo = openId
      ? `${SITE_URL}/bind?open_id=${encodeURIComponent(openId)}`
      : `${SITE_URL}/bind`;

    const { error: signUpError } = await supabase.auth.signUp({
      email,
      password,
      options: { emailRedirectTo: redirectTo },
    });

    if (signUpError) {
      setError(signUpError.message);
      setLoading(false);
      return;
    }

    setSent(true);
  }

  if (sent) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="bg-white p-8 rounded-xl shadow w-full max-w-sm text-center">
          <h1 className="text-2xl font-bold mb-4">查收确认邮件</h1>
          <p className="text-gray-500 text-sm">
            已发送确认邮件至 <strong>{email}</strong>，点击邮件中的链接完成注册并绑定飞书。
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="bg-white p-8 rounded-xl shadow w-full max-w-sm">
        <h1 className="text-2xl font-bold mb-6 text-center">注册 pi-matrix</h1>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <input
            type="email"
            placeholder="邮箱"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="border rounded-lg px-4 py-2 outline-none focus:ring-2 focus:ring-black"
          />
          <input
            type="password"
            placeholder="密码（至少 6 位）"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={6}
            className="border rounded-lg px-4 py-2 outline-none focus:ring-2 focus:ring-black"
          />
          {error && <p className="text-red-500 text-sm">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="bg-black text-white rounded-lg py-2 font-semibold hover:bg-gray-800 disabled:opacity-50"
          >
            {loading ? "注册中..." : "注册"}
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
