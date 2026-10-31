import "./globals.css";
import "./glass.css";
import React from "react";
import { DevHeader } from "@/components/DevHeader";
import { MainWrapper } from "@/components/MainWrapper";
import { AppBackground } from "@/components/ui/AppBackground";

// Fonts load in the browser (see the stylesheet link below) instead of at build time, so `next build`
// never needs network access to Google Fonts. The --font-* variables are defined in globals.css.
const FONTS_URL =
  "https://fonts.googleapis.com/css2?family=Inter+Tight:wght@300;400;500;600&display=swap";

export const metadata = {
  title: "TinyTravel — The price you see isn't the price you pay.",
  description: "Browser agents follow the price to the payment page as a guest and show you the proof.",
};

export const viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  // Single dark-blue theme. meta theme-color cannot use CSS variables; this is the sky-night base.
  themeColor: "#045A82",
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
      <body className="min-h-screen text-text-1 antialiased selection:bg-glass-strong selection:text-text-1">
        <AppBackground />
        <DevHeader />
        <MainWrapper>{children}</MainWrapper>
      </body>
    </html>
  );
}