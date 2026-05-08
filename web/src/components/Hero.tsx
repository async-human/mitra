"use client";

import Link from "next/link";
import { whatsAppHrefFor } from "@/lib/whatsapp";
import { ArrowDownIcon, BriefcaseIcon, WhatsAppIcon } from "./icons";
import { PhoneMockup } from "./PhoneMockup";
import { useAudience, type Audience } from "./AudienceContext";

const COPY = {
  candidate: {
    h1: (
      <>
        Stop sending CVs
        <br />
        into the void.
        <br />
        <em>Get introduced.</em>
      </>
    ),
    sub: "Mitra is your personal AI talent agent. A 2-minute conversation on WhatsApp — then we match you to India's best-funded startups and introduce you directly to the founder. No cold applications. No ghosting. Ever.",
    cta: {
      label: "Start on WhatsApp — free",
      icon: <WhatsAppIcon size={16} />,
      className: "btn-hero-p",
      href: whatsAppHrefFor("candidate"),
    },
  },
  founder: {
    h1: (
      <>
        Stop drowning in CVs.
        <br />
        Get <em>the right person</em>
        <br />
        introduced to you.
      </>
    ),
    sub: "Mitra is your always-on talent partner. We source, screen, and introduce pre-qualified candidates who are genuinely motivated to join a company like yours — not a pile of resumes with no context.",
    cta: {
      label: "List a role — first 2 hires free",
      icon: <BriefcaseIcon size={16} />,
      className: "btn-hero-p teal",
      href: whatsAppHrefFor("founder"),
    },
  },
} as const;

export function Hero() {
  const { audience, setAudience } = useAudience();
  const copy = COPY[audience];

  return (
    <section className="hero">
      <div className="hero-left">
        <div
          className="aud-tog"
          role="tablist"
          aria-label="I am a"
        >
          <button
            type="button"
            role="tab"
            aria-selected={audience === "candidate"}
            className={`tog-btn${audience === "candidate" ? " on" : ""}`}
            onClick={() => setAudience("candidate")}
          >
            I&apos;m looking for a role
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={audience === "founder"}
            className={`tog-btn${audience === "founder" ? " on" : ""}`}
            onClick={() => setAudience("founder")}
          >
            I&apos;m hiring
          </button>
        </div>

        <h1 className="hero-h1">{copy.h1}</h1>
        <p className="hero-sub">{copy.sub}</p>

        <div className="hero-ctas">
          <a
            href={copy.cta.href}
            target="_blank"
            rel="noopener noreferrer"
            className={copy.cta.className}
          >
            {copy.cta.icon}
            {copy.cta.label}
          </a>
          <Link href="#how" className="btn-hero-s">
            See how it works
            <ArrowDownIcon size={14} />
          </Link>
        </div>

        <div className="hero-proof">
          <div className="proof-item">
            <span className="proof-dot" />
            Free for candidates, always
          </div>
          <span className="proof-sep" />
          <div className="proof-item">
            <span className="proof-dot" />
            Avg. 8 days to first interview
          </div>
          <span className="proof-sep" />
          <div className="proof-item">
            <span className="proof-dot" />
            Zero ghosting — guaranteed
          </div>
          <span className="proof-sep" />
          <div className="proof-item">
            <span className="proof-dot" />
            Pan-India — remote & hybrid roles
          </div>
        </div>
      </div>

      <div className="hero-right" aria-hidden="true">
        <div className="hero-scene">
          <PhoneMockup layout="hero" />

          <div className="hero-float hf-1">
            <div className="hf-label green">Placed via Mitra</div>
            <div className="hf-quote">
              &ldquo;4 months, 60 applications, zero callbacks. Mitra had me
              talking to a founder in 4 days.&rdquo;
            </div>
            <div className="hf-person">
              <div
                className="hf-av"
                style={{ background: "linear-gradient(135deg,#1B5E5A,#237870)" }}
              >
                A
              </div>
              <div>
                <div className="hf-name">Aakash Verma</div>
                <div className="hf-role">Staff Engineer — now at Setu</div>
              </div>
            </div>
            <div className="hf-bar">
              <span className="hf-bdot" />
              Introduced · Offer accepted in 12 days
            </div>
          </div>

          <div className="hero-float hf-2">
            <div className="hf-label amber">Avg. time to hire</div>
            <div className="hf-big">
              8<sup>d</sup>
            </div>
            <div className="hf-desc">
              from first conversation
              <br />
              to interview booked
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
