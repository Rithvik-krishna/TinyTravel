import "./globals.css";
import React from "react";
import { DevHeader } from "@/components/DevHeader";
import { MainWrapper } from "@/components/MainWrapper";

export const metadata = {
  title: "TinyTravel — The price you see isn't the price you pay.",
  description: "Physics-based travel price verification probing directly to checkout.",
};

export const viewport = {
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-surface text-text antialiased selection:bg-brand/20 selection:text-brand">
        <DevHeader />
        <MainWrapper>{children}</MainWrapper>
      </body>
    </html>
  );
}
