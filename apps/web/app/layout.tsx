import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Green Lab Support",
  description: "Customer support agent for Green Lab (lab/research services).",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}