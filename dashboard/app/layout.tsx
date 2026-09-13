import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AgenticMesh Dashboard",
  description: "AI-accelerated incident triage with human-approved automated remediation",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="bg-slate-900 text-slate-50 min-h-screen">
        {children}
      </body>
    </html>
  );
}
