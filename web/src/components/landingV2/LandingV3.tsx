"use client";

import { useState } from "react";
import { NavV2 } from "./NavV2";
import { HeroV3 } from "./HeroV3";
import { DayJourneySection } from "./DayJourneySection";
import { ProblemV3 } from "./ProblemV3";
import { HowItWorksV3 } from "./HowItWorksV3";
import { MemorySectionV2 } from "./MemorySectionV2";
import { FounderQuotesV2 } from "./FounderQuotesV2";
import { CompanyHireCTASection } from "./CompanyHireCTASection";
import { ProofV2 } from "./ProofV2";
import { FAQV2 } from "./FAQV2";
import { FooterV2 } from "./FooterV2";
import s from "./landing-v2.module.css";

export type V2Audience = "candidate" | "company";

export function LandingV3() {
  const [audience, setAudience] = useState<V2Audience>("candidate");

  return (
    <div className={s.root} data-audience={audience}>
      <NavV2 audience={audience} onAudienceChange={setAudience} />
      <main>
        <HeroV3 audience={audience} />
        <ProblemV3 audience={audience} />
        <HowItWorksV3 key={audience} audience={audience} />
        <MemorySectionV2 audience={audience} />
        <DayJourneySection audience={audience} />
        {audience === "company" && <FounderQuotesV2 />}
        {audience === "company" && <CompanyHireCTASection />}
        <ProofV2 audience={audience} />
        <FAQV2 audience={audience} />
      </main>
      <FooterV2 />
    </div>
  );
}
