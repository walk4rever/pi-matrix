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
    <main className="min-h-screen bg-parchment flex items-center justify-center px-4">
      <div className="bg-ivory border border-border-cream rounded-2xl shadow-whisper w-full max-w-sm p-10 text-center">

        {(status === "waiting" || status === "binding") && (
          <>
            <div className="flex justify-center mb-6">
              <svg
                className="animate-spin h-8 w-8 text-stone-gray"
                viewBox="0 0 24 24"
                fill="none"
              >
                <circle
                  className="opacity-20"
                  cx="12" cy="12" r="10"
                  stroke="currentColor"
                  strokeWidth="3"
                />
                <path
                  className="opacity-80"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
                />
              </svg>
            </div>
            <h1 className="font-serif text-2xl font-medium text-nearblack mb-2" style={{ lineHeight: 1.2 }}>
              正在绑定
            </h1>
            <p className="text-stone-gray text-sm leading-relaxed">
              正在将您的飞书账号与 pi-matrix 绑定，请稍候...
            </p>
          </>
        )}

        {status === "done" && (
          <>
            <div className="text-5xl mb-6">🎉</div>
            <h1 className="font-serif text-2xl font-medium text-nearblack mb-2" style={{ lineHeight: 1.2 }}>
              绑定成功
            </h1>
            <p className="text-olive-gray text-sm leading-relaxed">
              您的数字员工正在准备中，<br />
              回飞书发消息，马上开始对话。
            </p>
            <div className="mt-8 pt-6 border-t border-border-cream">
              <p className="text-stone-gray text-xs leading-relaxed">
                此页面可以关闭
              </p>
            </div>
          </>
        )}

        {status === "error" && (
          <>
            <div className="text-5xl mb-6">⚠️</div>
            <h1 className="font-serif text-2xl font-medium text-nearblack mb-2" style={{ lineHeight: 1.2 }}>
              绑定失败
            </h1>
            <p className="text-[#b53333] text-sm leading-relaxed">{message}</p>
            <div className="mt-8 pt-6 border-t border-border-cream">
              <p className="text-stone-gray text-xs leading-relaxed">
                请重新点击邮件中的绑定链接
              </p>
            </div>
          </>
        )}

      </div>
    </main>
  );
}

export default function BindPage() {
  return (
    <Suspense>
      <BindForm />
    </Suspense>
  );
}
