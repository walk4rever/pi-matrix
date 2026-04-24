"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";

export default function ConsoleEntryPage() {
  const router = useRouter();

  useEffect(() => {
    let mounted = true;
    supabase.auth.getSession().then(({ data }) => {
      if (!mounted) return;
      if (data.session) {
        router.replace("/dashboard");
      } else {
        router.replace("/login");
      }
    });
    return () => {
      mounted = false;
    };
  }, [router]);

  return (
    <div className="auth-page">
      <div className="auth-card" style={{ textAlign: "center" }}>
        <div className="spinner">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" opacity="0.2" />
            <path fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" opacity="0.8" />
          </svg>
        </div>
        <div className="status-title">正在进入控制台</div>
        <p className="status-desc">正在检查登录状态，请稍候...</p>
      </div>
    </div>
  );
}

