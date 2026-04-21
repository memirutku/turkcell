import type { Metadata } from "next";
import "./globals.css";
import { ScreenReaderAnnouncer } from "@/components/a11y/ScreenReaderAnnouncer";
import { ThemeProvider } from "@/components/ThemeProvider";

export const metadata: Metadata = {
  title: "Umay Umay | Dijital Asistan",
  description:
    "Umay Umay: Fatura analizi, tarife değişikliği ve teknik destek için yapay zeka destekli dijital asistan.",
  keywords: ["Umay", "Umay", "AI", "dijital asistan", "fatura", "tarife"],
  icons: { icon: "/umay-amblem.png" },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="tr" suppressHydrationWarning>
      <body className="min-h-screen antialiased">
        {/* Skip to main content link for keyboard/screen reader users */}
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:px-4 focus:py-2 focus:bg-primary focus:text-primary-foreground focus:rounded-lg focus:outline-none focus:ring-2 focus:ring-ring"
        >
          Ana içeriği atla
        </a>
        <ThemeProvider>
          {children}
          <ScreenReaderAnnouncer />
        </ThemeProvider>
      </body>
    </html>
  );
}
