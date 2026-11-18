import type { Metadata } from "next";
import type { ReactNode } from "react";

import "./globals.css";

export const metadata: Metadata = {
  title: "Rwanda AI Tutor",
  description: "Curriculum-grounded tutor for Rwandan secondary schools.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-white font-sans text-slate-900 antialiased">{children}</body>
    </html>
  );
}
