"use client";

import { useState, useEffect, useRef, Fragment } from "react";
import { whatsAppHrefFor } from "@/lib/whatsapp";
import type { V2Audience } from "./LandingV2";
import s from "./landing-v2.module.css";

/* ── Typing hook ──────────────────────────────────────────── */

function useTyping(fullText: string, speed = 36) {
  const [displayed, setDisplayed] = useState("");
  const timerRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  useEffect(() => {
    let i = 0;
    setDisplayed("");
    if (timerRef.current) clearTimeout(timerRef.current);

    const tick = () => {
      if (i < fullText.length) {
        setDisplayed(fullText.slice(0, i + 1));
        i++;
        // Slight jitter makes it feel hand-typed rather than mechanical
        timerRef.current = setTimeout(tick, speed + Math.random() * 18);
      }
    };

    timerRef.current = setTimeout(tick, 180);
    return () => { if (timerRef.current) clearTimeout(timerRef.current); };
  }, [fullText, speed]);

  return displayed;
}

/* Render a typed string — handles \n as <br /> */
function TypedText({ text }: { text: string }) {
  return (
    <>
      {text.split("\n").map((line, i) => (
        <Fragment key={i}>{i > 0 && <br />}{line}</Fragment>
      ))}
    </>
  );
}

/* ── Icons ────────────────────────────────────────────────── */

function WhatsAppIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z" />
    </svg>
  );
}

/* ── Content ──────────────────────────────────────────────── */

const CONTENT = {
  candidate: {
    chip: "Now live · Engineers placed at Setu, CRED & Razorpay",
    headlineText: "The right introduction\nchanges everything.",
    sub: (
      <>
        Brief Mitra on what actually matters. We search hundreds of funded startups
        to find your genuine fit — then introduce you{" "}
        <strong>directly to the founder.</strong>{" "}
        No cold applications. No ghosting. Ever.
      </>
    ),
    ctaLabel: "Start on WhatsApp — free",
    ctaHref: whatsAppHrefFor("candidate"),
    ctaIcon: true,
    proof: [
      "Free for candidates, always",
      "Avg. 8 days to first interview",
      "Zero ghosting — guaranteed",
      "Pan-India · remote & hybrid",
    ],
  },
  company: {
    chip: "Now live · First 2 hires completely free",
    headlineText: "Hire the engineers\nothers can't reach.",
    sub: (
      <>
        Mitra speaks with engineers every day and understands them beyond their CV.
        Brief us on the role and get a shortlist of candidates who are{" "}
        <strong>genuinely interested, already qualified,</strong>{" "}
        and ready for a direct introduction — not a pipeline to manage.
      </>
    ),
    ctaLabel: "List a role — first 2 hires free",
    ctaHref: whatsAppHrefFor("founder"),
    ctaIcon: false,
    proof: [
      "First 2 hires free",
      "3–5 pre-qualified intros / week",
      "8% — half the agency rate",
      "90-day replacement guarantee",
    ],
  },
};

/* ── Component ────────────────────────────────────────────── */

export function HeroV2({ audience }: { audience: V2Audience }) {
  const c = CONTENT[audience];
  const typed = useTyping(c.headlineText);

  // Delay for sub/CTA/proof to appear — gives the typing a head start
  const afterDelay = Math.round(c.headlineText.length * 36 * 0.55);

  return (
    <section className={s.hero}>
      <div className={s.heroInner}>
        {/*
          key=audience remounts this div on audience switch,
          which resets all CSS animations and restarts typing.
        */}
        <div className={s.heroBody} key={audience}>

          {/* Chip fades in first */}
          <div
            className={`${s.heroChip} ${s.fadeUp}`}
            style={{ "--anim-delay": "0ms" } as React.CSSProperties}
          >
            <span className={s.chip}>
              <span className={s.chipDot} />
              {c.chip}
            </span>
          </div>

          {/* Headline types out — cursor blinks at end */}
          <h1 className={s.heroHeadline}>
            <TypedText text={typed} />
            <span className={s.heroCursor} aria-hidden="true" />
          </h1>

          {/* Sub, CTA, and proof fade in once typing has a head start */}
          <p
            className={`${s.heroSub} ${s.fadeUp}`}
            style={{ "--anim-delay": `${afterDelay}ms` } as React.CSSProperties}
          >
            {c.sub}
          </p>

          <div
            className={`${s.heroCtaRow} ${s.fadeUp}`}
            style={{ "--anim-delay": `${afterDelay + 120}ms` } as React.CSSProperties}
          >
            <a
              href={c.ctaHref}
              target="_blank"
              rel="noopener noreferrer"
              className={s.heroPrimaryCta}
            >
              {c.ctaIcon && <WhatsAppIcon />}
              {c.ctaLabel}
            </a>
            <a href="#how-it-works" className={s.heroSecondaryCta}>
              See how it works →
            </a>
          </div>

          <div
            className={`${s.heroProof} ${s.fadeUp}`}
            style={{ "--anim-delay": `${afterDelay + 240}ms` } as React.CSSProperties}
          >
            {c.proof.map((item, i) => (
              <Fragment key={item}>
                {i > 0 && <span className={s.heroProofSep} />}
                <div className={s.heroProofItem}>
                  <span className={s.heroProofDot} />
                  {item}
                </div>
              </Fragment>
            ))}
          </div>

        </div>
      </div>
    </section>
  );
}
