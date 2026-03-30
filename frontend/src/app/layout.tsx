import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Turkcell AI-Gen | Dijital Asistan",
  description:
    "Turkcell AI-Gen: Fatura analizi, tarife degisikligi ve teknik destek icin yapay zeka destekli dijital asistan.",
  keywords: ["Turkcell", "AI", "dijital asistan", "fatura", "tarife"],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="tr">
      <body className="min-h-screen bg-turkcell-gray text-turkcell-dark antialiased">
        {children}
      </body>
    </html>
  );
}
