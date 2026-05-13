"use client";

import { useEffect, useRef, useState } from "react";
import type { V2Audience } from "./LandingV2";
import s from "./landing-v2.module.css";

const CONTENT = {
  candidate: {
    label: "Memory",
    title: "Most tools see your CV.\nMitra builds your profile.",
    left: {
      heading: "What a recruiter sees",
      items: [
        "Job title and company name",
        "Years of experience",
        "Tech stack from your CV",
        "Current salary",
      ],
    },
    right: {
      heading: "What Mitra builds",
      items: [
        "Where you're actually headed — not just where you've been",
        "The environment you thrive in vs what drains you",
        "Whether your salary expectation shifted after hearing the market",
        "That you turned down a fintech role because of the sector, not the package",
        "How fast you make decisions and how you communicate under pressure",
        "What you're really optimising for in your next move",
      ],
    },
  },
  company: {
    label: "Memory",
    title: "Most tools track candidates.\nMitra learns how you hire.",
    left: {
      heading: "What a recruiter tracks",
      items: [
        "Candidates submitted",
        "Interviews scheduled",
        "JD requirements on file",
        "Pipeline stage",
      ],
    },
    right: {
      heading: "What Mitra learns",
      items: [
        "You respond fastest to engineers with strong startup-first backgrounds",
        "You consistently pass on FAANG pedigree without ownership evidence",
        "You value first-principles thinking over years of experience",
        "Your real notice-period tolerance is 45 days, not 30",
        "What your past successful hires had in common — and what they didn't",
      ],
    },
  },
};

export function MemorySectionV2({ audience }: { audience: V2Audience }) {
  const c = CONTENT[audience];
  const titleLines = c.title.split("\n");
  const sectionRef = useRef<HTMLElement>(null);
  const audienceReplaySkip = useRef(true);
  const [inView, setInView] = useState(false);

  // Fire when section scrolls into viewport
  useEffect(() => {
    const el = sectionRef.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([e]) => {
        if (e.isIntersecting) setInView(true);
      },
      { threshold: 0.12, rootMargin: "0px 0px -10% 0px" }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  // Re-run list/card entrance when global audience changes (skip first mount — that would cancel scroll-in motion)
  useEffect(() => {
    if (audienceReplaySkip.current) {
      audienceReplaySkip.current = false;
      return;
    }
    let cancelled = false;
    const raf = requestAnimationFrame(() => {
      if (!cancelled) setInView(false);
    });
    const t = setTimeout(() => {
      if (cancelled) return;
      const el = sectionRef.current;
      if (!el) return;
      const rect = el.getBoundingClientRect();
      if (rect.top < window.innerHeight && rect.bottom > 0) setInView(true);
    }, 50);
    return () => {
      cancelled = true;
      cancelAnimationFrame(raf);
      clearTimeout(t);
    };
  }, [audience]);

  return (
    <section className={s.sectionWrap} ref={sectionRef}>
      <div className={`${s.sectionInner} ${s.memorySectionBody} ${inView ? s.memorySectionInView : ""}`}>

        <p className={s.sectionLabel}>{c.label}</p>

        <h2 className={s.memoryTitle}>
          {titleLines[0]}
          {titleLines[1] && <><br /><span className={s.memoryTitleAccent}>{titleLines[1]}</span></>}
        </h2>

        <div className={s.memoryCard}>

          {/* Left — cold system data */}
          <div className={s.memoryColLeft}>
            <p className={s.memoryColLabel}>{c.left.heading}</p>
            <ul className={s.memoryList}>
              {c.left.items.map((item, i) => (
                <li
                  key={item}
                  className={`${s.memoryItem} ${s.memoryItemMuted} ${s.memoryItemLeft}`}
                  style={{ "--item-delay": `${260 + i * 65}ms` } as React.CSSProperties}
                >
                  <span className={s.memoryItemDash} aria-hidden="true">—</span>
                  {item}
                </li>
              ))}
            </ul>
          </div>

          <div className={s.memoryDivider} aria-hidden="true" />

          {/* Right — Mitra's rich profile */}
          <div className={s.memoryColRight}>
            <p className={`${s.memoryColLabel} ${s.memoryColLabelAccent}`}>{c.right.heading}</p>
            <ul className={s.memoryList}>
              {c.right.items.map((item, i) => (
                <li
                  key={item}
                  className={`${s.memoryItem} ${s.memoryItemRight}`}
                  style={{
                    "--item-delay": `${340 + i * 85}ms`,
                    "--dot-delay": `${i * 350}ms`,
                  } as React.CSSProperties}
                >
                  <span className={s.memoryItemDot} aria-hidden="true" />
                  {item}
                </li>
              ))}
            </ul>
          </div>

        </div>
      </div>
    </section>
  );
}
