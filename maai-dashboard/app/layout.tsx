import "./globals.css";
import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "MAAI — Clinician Dashboard",
  description: "Maternal mental-health screening triage",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <nav className="nav">
          <Link href="/" className="brand">MAAI</Link>
          <Link href="/">Overview</Link>
          <Link href="/alerts">Alert queue</Link>
          <Link href="/mothers">Mothers</Link>
        </nav>
        {children}
      </body>
    </html>
  );
}
