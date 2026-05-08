"use client";

import { whatsAppHrefFor } from "@/lib/whatsapp";
import { Reveal } from "./Reveal";
import { BriefcaseIcon, WhatsAppIcon } from "./icons";
import { useAudience } from "./AudienceContext";

const COPY = {
  candidate: {
    kicker: "Your next chapter starts here",
    h2: <>One conversation.<br /><em>One introduction.</em><br />Everything changes.</>,
    sub: "Mitra is free for candidates — always, no asterisk. A 2-minute WhatsApp conversation is all it takes to get started.",
    primary: { label: "Start on WhatsApp — free", href: whatsAppHrefFor("candidate"), icon: <WhatsAppIcon size={16} />, cls: "btn-fp" },
    secondary: { label: "I'm a founder hiring →", href: null as string | null },
    note: "Free for candidates · Pan-India · Remote & hybrid roles",
  },
  founder: {
    kicker: "Your next great hire is one intro away",
    h2: <>Stop drowning in CVs.<br /><em>Get the right person</em><br />introduced to you.</>,
    sub: "No contracts. No upfront fees. We activate within 24 hours and send 3–5 pre-qualified introductions weekly. 8% success fee, only when you hire.",
    primary: { label: "List a role — first 2 hires free", href: whatsAppHrefFor("founder"), icon: <BriefcaseIcon size={16} />, cls: "btn-fp btn-fp--amber" },
    secondary: { label: "I'm looking for a role →", href: null as string | null },
    note: "8% success fee · 90-day replacement guarantee · India-wide",
  },
} as const;

export function FinalCTA() {
  const { audience, setAudience } = useAudience();
  const copy = COPY[audience];
  const other = audience === "candidate" ? "founder" : "candidate";

  return (
    <section className="final-sec">
      <Reveal className="final-inner">
        <div className="final-kicker">{copy.kicker}</div>
        <h2 className="final-h2">{copy.h2}</h2>
        <p className="final-sub">{copy.sub}</p>
        <div className="final-btns">
          <a
            href={copy.primary.href}
            target="_blank"
            rel="noopener noreferrer"
            className={copy.primary.cls}
          >
            {copy.primary.icon}
            {copy.primary.label}
          </a>
        </div>
        <p className="final-bridge">
          <button
            type="button"
            className="final-bridge-link"
            onClick={() => setAudience(other)}
          >
            {copy.secondary.label}
          </button>
        </p>
        <p className="final-note">{copy.note}</p>
      </Reveal>
    </section>
  );
}
