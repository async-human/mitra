"use client";

import { useEffect, useRef, useState } from "react";
import type { V2Audience } from "./LandingV2";
import s from "./landing-v2.module.css";

const CONTENT = {
  candidate: {
    label: "Memory",
    title: "Most tools see your CV.",
    titleAccent: "Mitra builds your profile.",
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
    title: "Most tools track candidates.",
    titleAccent: "Mitra learns how you hire.",
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
  const sectionRef = useRef<HTMLElement>(null);
  const isFirstMount = useRef(true);
  const [inView, setInView] = useState(false);
  // Incrementing this key forces React to remount list items → CSS animations restart cleanly
  const [animKey, setAnimKey] = useState(0);

  // Scroll-triggered entry
  useEffect(() => {
    const el = sectionRef.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setInView(true);
          setAnimKey((k) => k + 1);
          obs.disconnect();
        }
      },
      { threshold: 0.05 }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  // Replay on audience change (skip initial mount)
  useEffect(() => {
    if (isFirstMount.current) {
      isFirstMount.current = false;
      return;
    }
    let cancelled = false;
    const raf = requestAnimationFrame(() => {
      if (cancelled) return;
      setInView(false);
      setTimeout(() => {
        if (cancelled) return;
        const el = sectionRef.current;
        if (!el) return;
        const { top, bottom } = el.getBoundingClientRect();
        if (top < window.innerHeight && bottom > 0) {
          setInView(true);
          setAnimKey((k) => k + 1);
        }
      }, 60);
    });
    return () => {
      cancelled = true;
      cancelAnimationFrame(raf);
    };
  }, [audience]);

  return (
    <section className={s.sectionWrap} ref={sectionRef}>
      <div className={`${s.sectionInner} ${s.memorySectionBody} ${inView ? s.memorySectionInView : ""}`}>

        <p className={s.sectionLabel}>{c.label}</p>

        <h2 className={s.memoryTitle}>
          <span className={s.memoryTitleLine}>{c.title}</span>
          <br />
          <span className={s.memoryTitleAccent}>{c.titleAccent}</span>
        </h2>

        <div className={s.memoryCard}>

          {/* Left — cold system snapshot */}
          <div className={s.memoryColLeft}>
            <div className={s.memoryColHeader}>
              <span className={s.memoryColHeaderDot} />
              <p className={s.memoryColLabel}>{c.left.heading}</p>
            </div>
            <ul className={s.memoryList}>
              {c.left.items.map((item, i) => (
                <li
                  key={`${animKey}-L-${i}`}
                  className={`${s.memoryItem} ${s.memoryItemLeft}`}
                  style={{ animationDelay: `${180 + i * 90}ms` } as React.CSSProperties}
                >
                  <span className={s.memoryRowNum} aria-hidden="true">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <span className={s.memoryItemText}>{item}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className={s.memoryDivider} aria-hidden="true">
            <span className={s.memoryDividerGlow} />
          </div>

          {/* Right — Mitra's live intelligence */}
          <div className={s.memoryColRight}>
            <div className={s.memoryColHeader}>
              <span className={`${s.memoryColHeaderDot} ${s.memoryColHeaderDotLive}`} />
              <p className={`${s.memoryColLabel} ${s.memoryColLabelAccent}`}>{c.right.heading}</p>
            </div>
            <ul className={s.memoryList}>
              {c.right.items.map((item, i) => (
                <li
                  key={`${animKey}-R-${i}`}
                  className={`${s.memoryItem} ${s.memoryItemRight}`}
                  style={{ animationDelay: `${360 + i * 120}ms` } as React.CSSProperties}
                >
                  <span className={s.memoryItemDot} aria-hidden="true" />
                  <span className={s.memoryItemText}>{item}</span>
                </li>
              ))}
            </ul>
          </div>

        </div>
      </div>
    </section>
  );
}
