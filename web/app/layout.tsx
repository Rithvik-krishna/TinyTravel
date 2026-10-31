import "./globals.css";
import React from "react";
import { DevHeader } from "@/components/DevHeader";
import { MainWrapper } from "@/components/MainWrapper";

// Fonts load in the browser (see the stylesheet link below) instead of at build time, so `next build`
// never needs network access to Google Fonts. The --font-* variables are defined in globals.css.
const FONTS_URL =
  "https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700;12..96,800&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&family=Figtree:wght@400;500;600;700&display=swap";

export const metadata = {
  title: "TinyTravel — The price you see isn't the price you pay.",
  description: "Browser agents follow the price to the payment page as a guest and show you the proof.",
};

export const viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  // meta theme-color cannot use CSS variables; these are the Ivory and Slate-900 page backgrounds.
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#FAF9F6" },
    { media: "(prefers-color-scheme: dark)", color: "#111827" },
  ],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        {/* eslint-disable-next-line @next/next/no-page-custom-font */}
        <link rel="stylesheet" href={FONTS_URL} />
      </head>
      <body className="min-h-screen bg-background text-ink antialiased selection:bg-brand-soft selection:text-ink">
        <DevHeader />
        <MainWrapper>{children}</MainWrapper>
      </body>
    </html>
  );
}