import "./globals.css";
import React from "react";
import { Bricolage_Grotesque, IBM_Plex_Sans, IBM_Plex_Mono } from "next/font/google";
import { DevHeader } from "@/components/DevHeader";
import { MainWrapper } from "@/components/MainWrapper";

const display = Bricolage_Grotesque({ subsets: ["latin"], weight: ["500", "700", "800"], variable: "--font-display", display: "swap" });
const body = IBM_Plex_Sans({ subsets: ["latin"], weight: ["400", "500", "600"], variable: "--font-body", display: "swap" });
const mono = IBM_Plex_Mono({ subsets: ["latin"], weight: ["400", "500"], variable: "--font-mono", display: "swap" });

export const metadata = {
  title: "TinyTravel — The price you see isn't the price you pay.",
  description: "Browser agents follow the price to the payment page as a guest and show you the proof.",
};

export const viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${display.variable} ${body.variable} ${mono.variable}`}>
      <body className="min-h-screen bg-surface text-text antialiased selection:bg-brand/20 selection:text-brand">
        <DevHeader />
        <MainWrapper>{children}</MainWrapper>
      </body>
    </html>
  );
}
