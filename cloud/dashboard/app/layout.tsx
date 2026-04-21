import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "pi-matrix",
  description: "您的专属爱马仕员工，在飞书候命。",
  icons: { icon: "/logo.svg" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh">
      <body>{children}</body>
    </html>
  );
}
