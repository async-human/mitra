"use client";

import { useState, useEffect, useRef, Fragment } from "react";
import Link from "next/link";
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

/* ── Content ──────────────────────────────────────────────── */

const CONTENT = {
  candidate: {
    chip: "Now live · Engineers placed at Setu, CRED & Razorpay",
    headlineText: "Your AI career companion.\nNot a job board.",
    sub: (
      <>
        Mitra doesn&apos;t reset between sessions. It learns your career trajectory,
        remembers what matters to you, and makes warm introductions that land —
        based on who you actually are,{" "}
        <strong>not just what&apos;s on your CV.</strong>
      </>
    ),
    cta: { label: "Get started — free", href: "/sign-in?role=candidate", external: false },
    proof: [
      "Free for candidates, always",
      "Avg. 8 days to first interview",
      "Zero ghosting — guaranteed",
      "Pan-India · remote & hybrid",
    ],
  },
  company: {
    chip: "Now live · First 2 hires completely free",
    headlineText: "An AI hiring partner\nthat learns how you hire.",
    sub: (
      <>
        Mitra speaks with engineers every day and understands them beyond their CV.
        Over time it learns your hiring style — who you respond to, who you pass on,
        and why — so every shortlist gets{" "}
        <strong>sharper with each placement.</strong>
      </>
    ),
    cta: { label: "List a role — first 2 hires free", href: whatsAppHrefFor("founder"), external: true },
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
            {c.cta.external ? (
              <a href={c.cta.href} target="_blank" rel="noopener noreferrer" className={s.heroPrimaryCta}>
                {c.cta.label}
              </a>
            ) : (
              <Link href={c.cta.href} className={s.heroPrimaryCta}>
                {c.cta.label}
              </Link>
            )}
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
