"use client";

import React from "react";
import { usePathname } from "next/navigation";

export function MainWrapper({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <main className={pathname !== "/onboarding" ? "w-full" : "max-w-5xl mx-auto p-4"}>
      {children}
    </main>
  );
}
