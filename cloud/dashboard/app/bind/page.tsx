"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";

function BindForm() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const openId = searchParams.get("open_id") ?? "";

  const [status, setStatus] = useState<"idle" | "loading" | "done" | "error">("idle");
  const [message, setMessage] = useState("");

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      if (!data.session) router.replace(`/register?open_id=${encodeURIComponent(openId)}`);
    });
  }, [openId, router]);

  async function handleBind() {
    if (!openId) {
      setMessage("缺少飞书 open_id，请从飞书消息中的链接进入此页面。");
      setStatus("error");
      return;
    }

    setStatus("loading");
    const { data: { session } } = await supabase.auth.getSession();
    if (!session) {
      router.replace(`/register?open_id=${encodeURIComponent(openId)}`);
      return;
    }

    const res = await fetch("/pm/api/feishu/bind", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${session.access_token}`,
      },
      body: JSON.stringify({ open_id: openId }),
    });

    if (res.ok) {
      setStatus("done");
      setMessage("绑定成功！回飞书发消息，您的数字员工马上上线。");
    } else {
      const body = await res.json().catch(() => ({}));
      setMessage(body.detail ?? "绑定失败，请重试。");
      setStatus("error");
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="bg-white p-8 rounded-xl shadow w-full max-w-sm text-center">
        <h1 className="text-2xl font-bold mb-4">绑定飞书账号</h1>
        <p className="text-gray-500 mb-6 text-sm">
          点击下方按钮，将您的飞书账号与 pi-matrix 绑定。
        </p>

        {status === "done" ? (
          <p className="text-green-600 font-semibold">{message}</p>
        ) : (
          <>
            {message && <p className="text-red-500 text-sm mb-4">{message}</p>}
            <button
              onClick={handleBind}
              disabled={status === "loading"}
              className="w-full bg-black text-white rounded-lg py-2 font-semibold hover:bg-gray-800 disabled:opacity-50"
            >
              {status === "loading" ? "绑定中..." : "绑定飞书"}
            </button>
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
