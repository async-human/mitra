"use client";

import { useState } from "react";
import { NavV2 } from "./NavV2";
import { HeroV2 } from "./HeroV2";
import { DayJourneySection } from "./DayJourneySection";
import { ProblemSectionV2 } from "./ProblemSectionV2";
import { HowItWorksV2 } from "./HowItWorksV2";
import { PhilosophySectionV2 } from "./PhilosophySectionV2";
import { MemorySectionV2 } from "./MemorySectionV2";
import { RoadmapSectionV2 } from "./RoadmapSectionV2";
import { CompanyHireCTASection } from "./CompanyHireCTASection";
import { FounderQuotesV2 } from "./FounderQuotesV2";
import { ProofV2 } from "./ProofV2";
import { FAQV2 } from "./FAQV2";
import { FooterV2 } from "./FooterV2";
import s from "./landing-v2.module.css";

export type V2Audience = "candidate" | "company";

export function LandingV2() {
  const [audience, setAudience] = useState<V2Audience>("candidate");

  return (
    <div className={s.root} data-audience={audience}>
      <NavV2 audience={audience} onAudienceChange={setAudience} />
      <main>
        <HeroV2 audience={audience} />
        <DayJourneySection audience={audience} />
        <ProblemSectionV2 audience={audience} />
        <HowItWorksV2 audience={audience} />
        <PhilosophySectionV2 audience={audience} />
        <MemorySectionV2 audience={audience} />
        {audience === "company" && <FounderQuotesV2 />}
        <RoadmapSectionV2 />
        {audience === "company" && <CompanyHireCTASection />}
        <ProofV2 audience={audience} />
        <FAQV2 audience={audience} />
      </main>
      <FooterV2 />
    </div>
  );
}
