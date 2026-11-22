import type { Metadata } from "next";
import { Figtree, Syne } from "next/font/google";
import "./globals.css";

const display = Syne({
  subsets: ["latin"],
  variable: "--font-display",
  weight: ["500", "600", "700"],
});

const body = Figtree({
  subsets: ["latin"],
  variable: "--font-body",
  weight: ["400", "500", "600"],
});

export const metadata: Metadata = {
  title: "Baseline — Oura trends beyond the app",
  description:
    "Personal readiness, sleep debt, HRV, and recovery trends from your Oura ring — clearer patterns than the stock app.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className={`${display.variable} ${body.variable} antialiased`}>{children}</body>
    </html>
  );
}
