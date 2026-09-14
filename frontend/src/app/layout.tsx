import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "IRONCLAD — Autonomous Retainage & Lien-Discharge Sentinel",
  description:
    "Institutional-grade tri-track construction compliance cascade that intercepts AIA G702/G703 draw requests, deterministically audits retainage math and lien waiver chain-of-custody, and surfaces a zero-chat executive decision console.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="bg-[#0B0F19] text-gray-100 min-h-screen antialiased selection:bg-blue-600 selection:text-white">
        {children}
      </body>
    </html>
  );
}
