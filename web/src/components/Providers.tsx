"use client";

import type { ReactNode } from "react";
import { ThemeProvider } from "next-themes";
import { SessionProvider } from "next-auth/react";
import { AudienceProvider } from "./AudienceContext";
import { CookieBanner } from "./CookieBanner";
import { WhatsAppGate } from "./WhatsAppGate";

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
        <WhatsAppGate />
      </ThemeProvider>
    </SessionProvider>
  );
}
