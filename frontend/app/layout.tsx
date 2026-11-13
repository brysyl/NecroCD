import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";

export const metadata: Metadata = {
  title: "NecroCD | SRE Control Room",
  description: "Autonomous SRE git graveyard",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-zinc-950 text-zinc-300 antialiased">{children}</body>
    </html>
  );
}
