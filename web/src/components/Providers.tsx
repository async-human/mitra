"use client";

import type { ReactNode } from "react";
import { ThemeProvider } from "next-themes";
import { AudienceProvider } from "./AudienceContext";

export function Providers({ children }: { children: ReactNode }) {
  return (
    <ThemeProvider
      attribute="data-theme"
      defaultTheme="system"
      enableSystem
      disableTransitionOnChange
      storageKey="mitra-theme"
    >
      <AudienceProvider>{children}</AudienceProvider>
    </ThemeProvider>
  );
}
