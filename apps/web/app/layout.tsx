import type { Metadata } from "next";
import { Newsreader, Outfit } from "next/font/google";
import { getLocale } from "next-intl/server";
import type { ReactNode } from "react";

import "katex/dist/katex.min.css";

import "./globals.css";

const outfit = Outfit({
  subsets: ["latin"],
  variable: "--font-outfit",
  display: "swap",
});

const newsreader = Newsreader({
  subsets: ["latin"],
  variable: "--font-newsreader",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Rwanda AI Tutor",
  description: "Curriculum-grounded tutor for Rwandan secondary schools.",
};

export default async function RootLayout({ children }: { children: ReactNode }) {
  const locale = await getLocale();
  return (
    <html
      lang={locale}
      className={`${outfit.variable} ${newsreader.variable}`}
      suppressHydrationWarning
    >
      <body className="bg-paper font-sans text-ink antialiased">{children}</body>
    </html>
  );
}
