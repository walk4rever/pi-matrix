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
    <div className="auth-page">
      <div className="auth-card">
        {(status === "waiting" || status === "binding") && (
          <>
            <div className="spinner">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" opacity="0.2" />
                <path fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" opacity="0.8" />
              </svg>
            </div>
            <div className="status-title">正在绑定</div>
            <p className="status-desc">正在将您的飞书账号与 pi-matrix 绑定，请稍候...</p>
          </>
        )}

        {status === "done" && (
          <>
            <div className="status-icon">🎉</div>
            <div className="status-title">绑定成功</div>
            <p className="status-desc">
              您的数字员工正在准备中，<br />
              回飞书发消息，马上开始对话。
            </p>
            <div className="status-footer">此页面可以关闭</div>
          </>
        )}

        {status === "error" && (
          <>
            <div className="status-icon">⚠️</div>
            <div className="status-title">绑定失败</div>
            <p className="status-desc" style={{ color: "#b53333" }}>{message}</p>
            <div className="status-footer">请重新点击邮件中的绑定链接</div>
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
