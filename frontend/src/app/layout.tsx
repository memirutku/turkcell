import type { Metadata } from "next";
import "./globals.css";
import { ScreenReaderAnnouncer } from "@/components/a11y/ScreenReaderAnnouncer";

export const metadata: Metadata = {
  title: "Turkcell AI-Gen | Dijital Asistan",
  description:
    "Turkcell AI-Gen: Fatura analizi, tarife degisikligi ve teknik destek icin yapay zeka destekli dijital asistan.",
  keywords: ["Turkcell", "AI", "dijital asistan", "fatura", "tarife"],
  icons: { icon: "/favicon.svg" },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="tr">
      <body className="min-h-screen bg-turkcell-gray text-turkcell-dark antialiased">
        {/* Skip to main content link for keyboard/screen reader users */}
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:px-4 focus:py-2 focus:bg-turkcell-blue focus:text-white focus:rounded-lg focus:outline-none focus:ring-2 focus:ring-turkcell-yellow"
        >
          Ana icerigi atla
        </a>
        {children}
        <ScreenReaderAnnouncer />
      </body>
    </html>
  );
}
