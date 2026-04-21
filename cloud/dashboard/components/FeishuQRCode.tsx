"use client";

import { useEffect, useRef } from "react";
import QRCode from "qrcode";

const FEISHU_APPLINK = "https://applink.feishu.cn/T95H55yR3eVb";

export default function FeishuQRCode() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (!canvasRef.current) return;
    QRCode.toCanvas(canvasRef.current, FEISHU_APPLINK, {
      width: 160,
      margin: 2,
      color: { dark: "#3d2c1e", light: "#f5f4ed" },
    });
  }, []);

  return (
    <div className="qr-wrap">
      <canvas ref={canvasRef} />
      <p className="qr-label">打开飞书扫码，给 Bot 发消息后获取注册卡</p>
    </div>
  );
}
