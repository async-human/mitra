"use client";

import { whatsAppHrefFor } from "@/lib/whatsapp";
import { BriefcaseIcon, WhatsAppIcon } from "./icons";

export function StickyMobileCta() {
  return (
    <div className="sticky-wa" role="navigation" aria-label="WhatsApp shortcuts">
      <a
        href={whatsAppHrefFor("candidate")}
        className="sticky-wa-primary"
        target="_blank"
        rel="noopener noreferrer"
      >
        <WhatsAppIcon size={15} aria-hidden={true} />
        Find a role
      </a>
      <a
        href={whatsAppHrefFor("founder")}
        className="sticky-wa-secondary"
        target="_blank"
        rel="noopener noreferrer"
      >
        <BriefcaseIcon size={15} aria-hidden={true} />
        Hiring
      </a>
      <a
        href={whatsAppHrefFor("general")}
        className="sticky-wa-tertiary"
        target="_blank"
        rel="noopener noreferrer"
      >
        Ask a question
      </a>
    </div>
  );
}
