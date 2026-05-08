"use client";

import { createContext, useContext, useState, type ReactNode } from "react";

export type Audience = "candidate" | "founder";

interface AudienceCtxValue {
  audience: Audience;
  setAudience: (a: Audience) => void;
}

const Ctx = createContext<AudienceCtxValue>({ audience: "candidate", setAudience: () => {} });

export function AudienceProvider({ children }: { children: ReactNode }) {
  const [audience, setAudience] = useState<Audience>("candidate");
  return <Ctx.Provider value={{ audience, setAudience }}>{children}</Ctx.Provider>;
}

export function useAudience() {
  return useContext(Ctx);
}
