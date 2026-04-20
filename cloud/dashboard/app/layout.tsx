import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "pi-matrix",
  description: "Your digital employee dashboard",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh">
      <body>{children}</body>
    </html>
  );
}
