"use client";

import { useState, useEffect, useRef, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { supabase } from "@/lib/supabase";
import type { Session } from "@supabase/supabase-js";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "https://relay.air7.fun/pm/api";

function BindForm() {
  const searchParams = useSearchParams();
  const openId = searchParams.get("open_id") ?? "";

  const [status, setStatus] = useState<"waiting" | "binding" | "done" | "error">("waiting");
  const [message, setMessage] = useState("");
  const attempted = useRef(false);

  async function bind(session: Session) {
    if (attempted.current) return;
    attempted.current = true;
    setStatus("binding");

    if (!openId) {
      setMessage("缺少飞书 open_id，请从飞书消息中的链接进入此页面。");
      setStatus("error");
      return;
    }

    const res = await fetch(`${API_URL}/feishu/bind`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${session.access_token}`,
      },
      body: JSON.stringify({ open_id: openId }),
    });

    if (res.ok) {
      setStatus("done");
      setMessage("绑定成功！回飞书发消息，您的数字员工马上响应。");
    } else {
      const body = await res.json().catch(() => ({}));
      setMessage(body.detail ?? "绑定失败，请重试。");
      setStatus("error");
    }
  }

  useEffect(() => {
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      if ((event === "SIGNED_IN" || event === "INITIAL_SESSION") && session) {
        bind(session);
      } else if (event === "INITIAL_SESSION" && !session) {
        setMessage("登录已过期，请重新点击邮件中的链接。");
        setStatus("error");
      }
    });
    return () => subscription.unsubscribe();
  }, []);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="bg-white p-8 rounded-xl shadow w-full max-w-sm text-center">
        <h1 className="text-2xl font-bold mb-4">绑定飞书账号</h1>

        {status === "waiting" || status === "binding" ? (
          <>
            <div className="flex justify-center mb-4">
              <svg className="animate-spin h-8 w-8 text-gray-400" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
              </svg>
            </div>
            <p className="text-gray-500 text-sm">正在绑定中，请稍候...</p>
          </>
        ) : status === "done" ? (
          <>
            <div className="text-4xl mb-4">🎉</div>
            <p className="text-green-600 font-semibold">{message}</p>
          </>
        ) : (
          <>
            <div className="text-4xl mb-4">⚠️</div>
            <p className="text-red-500 text-sm">{message}</p>
          </>
        )}
      </div>
    </div>
  );
}

export default function BindPage() {
  return (
    <Suspense>
      <BindForm />
    </Suspense>
  );
}
