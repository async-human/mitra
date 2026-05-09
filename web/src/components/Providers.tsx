"use client";

import type { ReactNode } from "react";
import { ThemeProvider } from "next-themes";
import { SessionProvider } from "next-auth/react";
import { AudienceProvider } from "./AudienceContext";
import { CookieBanner } from "./CookieBanner";

export function Providers({ children }: { children: ReactNode }) {
  return (
    <SessionProvider>
      <ThemeProvider
        attribute="data-theme"
        defaultTheme="system"
        enableSystem
        disableTransitionOnChange
        storageKey="mitra-theme"
      >
        <AudienceProvider>{children}</AudienceProvider>
        <CookieBanner />
      </ThemeProvider>
    </SessionProvider>
  );
}
